from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from scripts.security_http_probe import SecurityHttpProbe, SecurityHttpProbeError


class SecureProbeHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/api/v1/rsot/resource-taxonomy":
            self.send_response(401)
            self.end_headers()
            return
        self.send_response(200)
        if self.path == "/":
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format: str, *args: object) -> None:
        del format, args


class InsecureProbeHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format: str, *args: object) -> None:
        del format, args


class TestSecurityHttpProbe:
    @staticmethod
    def _start(handler: type[BaseHTTPRequestHandler]) -> tuple[ThreadingHTTPServer, str]:
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        return server, f"http://{host}:{port}"

    def test_live_probe_accepts_expected_statuses_and_headers(self) -> None:
        server, base_url = self._start(SecureProbeHandler)
        try:
            results = SecurityHttpProbe(timeout_seconds=2).assert_secure(base_url, base_url)
        finally:
            server.shutdown()
            server.server_close()

        assert len(results) == 6
        assert all(result.passed for result in results)

    def test_live_probe_rejects_anonymous_access_and_missing_headers(self) -> None:
        server, base_url = self._start(InsecureProbeHandler)
        try:
            with pytest.raises(SecurityHttpProbeError) as exc_info:
                SecurityHttpProbe(timeout_seconds=2).assert_secure(base_url, base_url)
        finally:
            server.shutdown()
            server.server_close()

        assert "expected 401" in str(exc_info.value)
        assert "content-security-policy" in str(exc_info.value)

    def test_security_probe_script_is_packaged_in_source_distribution(self) -> None:
        assert Path("scripts/security_http_probe.py").is_file()
        assert Path("scripts/release_security_audit.py").is_file()
