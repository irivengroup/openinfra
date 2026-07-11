from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = (
    ROOT / "web/src/main.jsx",
    ROOT / "src/openinfra/interfaces/rendering/static/assets/openinfra-web.js",
)


def test_rag_is_grouped_under_rsot_with_route_parity_and_download() -> None:
    operations = (
        "rag-document-upsert",
        "rag-documents",
        "rag-document-get",
        "rag-document-deactivate",
        "rag-rsot-sync",
        "rag-query",
        "rag-answers",
        "rag-answer-get",
        "rag-job-create",
        "rag-jobs",
        "rag-job-get",
        "rag-job-run",
        "rag-job-artifact",
    )
    routes = (
        "/v1/rag/documents/upsert",
        "/v1/rag/documents",
        "/v1/rag/documents/get",
        "/v1/rag/documents/deactivate",
        "/v1/rag/index/rsot",
        "/v1/rag/query",
        "/v1/rag/answers",
        "/v1/rag/answers/get",
        "/v1/rag/jobs/create",
        "/v1/rag/jobs",
        "/v1/rag/jobs/get",
        "/v1/rag/jobs/run",
        "/v1/rag/jobs/artifact",
    )
    for path in SOURCES:
        source = path.read_text(encoding="utf-8")
        for operation in operations:
            assert operation in source
        for route in routes:
            assert route in source
        assert "Assistant gouverné" in source
        assert "Index de connaissances" in source
        assert "Imports / exports RAG" in source
        assert "rag-job-artifact" in source and "download" in source
        assert "id: 'rag'" not in source and 'id: "rag"' not in source


def test_rag_forms_use_validation_controls_and_no_destructive_action() -> None:
    for path in SOURCES:
        source = path.read_text(encoding="utf-8")
        assert "required_permissions" in source
        assert "metadata" in source
        assert "type: 'json'" in source or 'type: "json"' in source
        assert "question" in source
        assert "deactivate_missing" in source
        assert "rag-" in source
        assert "/v1/rag/execute" not in source
        assert "/v1/rag/remediate" not in source
