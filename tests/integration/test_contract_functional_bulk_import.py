from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.application.source_of_truth_services import GetSourceObjectCommand
from openinfra.domain.data_import import ImportFormat
from openinfra.infrastructure.import_parsers import ImportDatasetParser
from openinfra.interfaces.http_api import OpenInfraThreadingServer

_CSV_MAPPING = {
    "key": "asset_key",
    "kind": "kind",
    "display_name": "name",
    "source": "source",
    "tags": "tags",
    "attributes.serial": "serial",
    "attributes.critical": "critical",
}
_XLSX_MAPPING = {
    "key": "asset_key",
    "kind": "kind",
    "display_name": "name",
    "source": "literal:xlsx_import",
}


class _BlockingParser:
    def __init__(self, delegate: ImportDatasetParser) -> None:
        self._delegate = delegate
        self.entered = threading.Event()
        self.release = threading.Event()
        self._block_once = True

    def parse(self, path: Path, import_format: ImportFormat) -> tuple[dict[str, str], ...]:
        return tuple(self.iter_rows(path, import_format))

    def iter_rows(
        self,
        path: Path,
        import_format: ImportFormat,
        *,
        max_bytes: int | None = None,
    ) -> Iterator[dict[str, str]]:
        for row in self._delegate.iter_rows(path, import_format, max_bytes=max_bytes):
            if self._block_once:
                self._block_once = False
                self.entered.set()
                if not self.release.wait(timeout=5):
                    raise TimeoutError("bulk import test parser was not released")
            yield row


def test_tst_func_0003_async_bulk_import_csv_xlsx_is_traceable_restartable_and_non_blocking(
    tmp_path: Path,
) -> None:
    token = "bulk-import-admin-token-0123456789"
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "bulk-import-admin", ("admin",), token)
    )
    blocking_parser = _BlockingParser(ImportDatasetParser())
    app.import_service._parser = blocking_parser
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        csv_payload = (
            b"asset_key,kind,name,source,tags,serial,critical\n"
            b"device/async-csv-001,device,Async CSV 001,csv_import,prod,SN-CSV-001,true\n"
        )
        first = _upload(
            base,
            token,
            payload=csv_payload,
            filename="bulk.csv",
            import_format="csv",
            mapping=_CSV_MAPPING,
            idempotency_key="tst-func-0003-csv",
        )
        replayed = _upload(
            base,
            token,
            payload=csv_payload,
            filename="bulk.csv",
            import_format="csv",
            mapping=_CSV_MAPPING,
            idempotency_key="tst-func-0003-csv",
        )
        assert first["job"]["status"] == "queued"
        assert replayed["job"]["id"] == first["job"]["id"]
        assert first["source_artifact"]["size_bytes"] == len(csv_payload)

        worker_result: dict[str, object] = {}

        def run_worker() -> None:
            worker_result.update(
                _post_json(
                    base + "/api/v1/async/workers/imports/run-once",
                    {"tenant_id": "default", "worker_id": "imports-worker-001"},
                    token,
                )
            )

        worker_thread = threading.Thread(target=run_worker, daemon=True)
        worker_thread.start()
        assert blocking_parser.entered.wait(timeout=5)

        health = _get_json(base + "/health")
        in_progress = _status(base, token, str(first["job"]["id"]))
        assert health["status"] == "ok"
        assert in_progress["job"]["status"] == "leased"
        assert in_progress["result"] is None

        blocking_parser.release.set()
        worker_thread.join(timeout=10)
        assert not worker_thread.is_alive()
        assert worker_result["item"]["status"] == "completed"

        csv_status = _status(base, token, str(first["job"]["id"]))
        csv_report = csv_status["result"]["report"]
        assert csv_status["job"]["status"] == "completed"
        assert csv_report["status"] == "applied"
        assert csv_report["checkpoint"]["next_row_number"] == 2
        assert csv_report["create_count"] == 1
        csv_object = app.source_of_truth_service.get_object(
            GetSourceObjectCommand("default", token, "device/async-csv-001")
        )
        assert csv_object["attributes"]["serial"] == "SN-CSV-001"

        xlsx_payload = _minimal_xlsx_bytes()
        xlsx = _upload(
            base,
            token,
            payload=xlsx_payload,
            filename="bulk.xlsx",
            import_format="xlsx",
            mapping=_XLSX_MAPPING,
            idempotency_key="tst-func-0003-xlsx",
        )
        completed = _post_json(
            base + "/api/v1/async/workers/imports/run-once",
            {"tenant_id": "default", "worker_id": "imports-worker-002"},
            token,
        )
        assert completed["item"]["status"] == "completed"
        xlsx_status = _status(base, token, str(xlsx["job"]["id"]))
        assert xlsx_status["result"]["report"]["format"] == "xlsx"
        assert xlsx_status["result"]["report"]["status"] == "applied"
        xlsx_object = app.source_of_truth_service.get_object(
            GetSourceObjectCommand("default", token, "device/async-xlsx-001")
        )
        assert xlsx_object["display_name"] == "Async XLSX 001"

        project_root = Path(__file__).parents[2]
        for frontend in (
            project_root / "web/src/domains/data.js",
            project_root
            / "src/openinfra/interfaces/rendering/static/assets/domains/data.js",
        ):
            source = frontend.read_text(encoding="utf-8")
            assert "import-async-bulk-submit" in source
            assert "import-async-bulk-status" in source
            assert "/v1/imports/async-bulk-datasets" in source
            assert '"binaryUpload": true' in source
            assert '"authField"' not in source
            assert "admin_token" not in source
            assert "Jeton administrateur" not in source
            assert '"maxSizeBytes":536870912' in source
    finally:
        blocking_parser.release.set()
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)


def test_async_bulk_import_http_contract_rejects_unsafe_or_conflicting_requests(
    tmp_path: Path,
) -> None:
    token = "bulk-import-security-token-01234567"
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "bulk-security", ("admin",), token)
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        payload = (
            b"asset_key,kind,name,source\n"
            b"device/security-001,device,Security 001,csv_import\n"
        )
        query = {
            "tenant_id": "default",
            "format": "csv",
            "mapping_json": json.dumps(
                {
                    "key": "asset_key",
                    "kind": "kind",
                    "display_name": "name",
                    "source": "source",
                }
            ),
            "apply": "false",
            "idempotency_key": "security-import-001",
        }
        url = base + "/api/v1/imports/async-bulk-datasets?" + urllib.parse.urlencode(query)
        status, error = _request_error(
            urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Content-Type": "text/csv",
                    "X-OpenInfra-Filename": "security.csv",
                },
                method="POST",
            )
        )
        assert status == 401
        assert "token" in str(error["error"]).lower()

        invalid_format = dict(query, format="json", idempotency_key="security-import-002")
        status, error = _raw_upload_error(
            base, token, payload, "security.json", invalid_format
        )
        assert status == 400
        assert "only CSV and XLSX" in str(error["error"])

        invalid_filename = dict(query, idempotency_key="security-import-003")
        status, error = _raw_upload_error(
            base, token, payload, "../security.csv", invalid_filename
        )
        assert status == 400
        assert "filename" in str(error["error"])

        first = _upload(
            base,
            token,
            payload=payload,
            filename="security.csv",
            import_format="csv",
            mapping={
                "key": "asset_key",
                "kind": "kind",
                "display_name": "name",
                "source": "source",
            },
            idempotency_key="security-import-conflict",
        )
        assert first["job"]["status"] == "queued"
        changed = payload.replace(b"Security 001", b"Security 002")
        conflict_query = dict(query, idempotency_key="security-import-conflict")
        status, error = _raw_upload_error(
            base, token, changed, "security.csv", conflict_query
        )
        assert status == 400
        assert "idempotency key conflicts" in str(error["error"])

        status, error = _request_error(
            urllib.request.Request(
                base
                + "/api/v1/imports/async-bulk-status?"
                + urllib.parse.urlencode(
                    {"tenant_id": "default", "job_id": first["job"]["id"]}
                )
            )
        )
        assert status == 401
        assert "token" in str(error["error"]).lower()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _upload(
    base: str,
    token: str,
    *,
    payload: bytes,
    filename: str,
    import_format: str,
    mapping: dict[str, str],
    idempotency_key: str,
) -> dict[str, Any]:
    query = urllib.parse.urlencode(
        {
            "tenant_id": "default",
            "actor": "pytest",
            "format": import_format,
            "mapping_json": json.dumps(mapping, separators=(",", ":")),
            "apply": "true",
            "idempotency_key": idempotency_key,
            "batch_size": "5000",
            "checkpoint_interval": "25000",
            "sample_limit": "100",
            "max_attempts": "3",
        }
    )
    request = urllib.request.Request(
        base + "/api/v1/imports/async-bulk-datasets?" + query,
        data=payload,
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": (
                "text/csv"
                if import_format == "csv"
                else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            "X-OpenInfra-Filename": urllib.parse.quote(filename),
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        assert response.status == 202
        result = json.loads(response.read().decode("utf-8"))
    assert isinstance(result, dict)
    return result


def _status(base: str, token: str, job_id: str) -> dict[str, Any]:
    query = urllib.parse.urlencode({"tenant_id": "default", "job_id": job_id})
    return _get_json(
        base + "/api/v1/imports/async-bulk-status?" + query,
        token=token,
    )


def _get_json(url: str, token: str | None = None) -> dict[str, Any]:
    headers = {} if token is None else {"Authorization": "Bearer " + token}
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=5) as response:
        result = json.loads(response.read().decode("utf-8"))
    assert isinstance(result, dict)
    return result


def _post_json(url: str, payload: dict[str, object], token: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + token},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        result = json.loads(response.read().decode("utf-8"))
    assert isinstance(result, dict)
    return result


def _minimal_xlsx_bytes() -> bytes:
    worksheet = """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1">
      <c r="A1" t="inlineStr"><is><t>asset_key</t></is></c>
      <c r="B1" t="inlineStr"><is><t>kind</t></is></c>
      <c r="C1" t="inlineStr"><is><t>name</t></is></c>
    </row>
    <row r="2">
      <c r="A2" t="inlineStr"><is><t>device/async-xlsx-001</t></is></c>
      <c r="B2" t="inlineStr"><is><t>device</t></is></c>
      <c r="C2" t="inlineStr"><is><t>Async XLSX 001</t></is></c>
    </row>
  </sheetData>
</worksheet>
"""
    from io import BytesIO

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as workbook:
        workbook.writestr("xl/worksheets/sheet1.xml", worksheet)
    return buffer.getvalue()


def _raw_upload_error(
    base: str,
    token: str,
    payload: bytes,
    filename: str,
    query: dict[str, str],
) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(
        base + "/api/v1/imports/async-bulk-datasets?" + urllib.parse.urlencode(query),
        data=payload,
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/octet-stream",
            "X-OpenInfra-Filename": urllib.parse.quote(filename),
        },
        method="POST",
    )
    return _request_error(request)


def _request_error(request: urllib.request.Request) -> tuple[int, dict[str, Any]]:
    try:
        urllib.request.urlopen(request, timeout=10)
    except urllib.error.HTTPError as exc:
        payload = json.loads(exc.read().decode("utf-8"))
        assert isinstance(payload, dict)
        return exc.code, payload
    raise AssertionError("request unexpectedly succeeded")
