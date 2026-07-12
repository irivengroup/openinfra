from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass


class SecurityHttpProbeError(Exception):
    """Raised when a live HTTP security contract is violated."""


@dataclass(frozen=True, slots=True)
class HttpProbeResult:
    name: str
    passed: bool
    detail: str

    def as_dict(self) -> dict[str, object]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


class SecurityHttpProbe:
    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._timeout_seconds = timeout_seconds

    def run(self, api_base_url: str, web_base_url: str) -> tuple[HttpProbeResult, ...]:
        api = api_base_url.rstrip("/")
        web = web_base_url.rstrip("/")
        results = (
            self._expect_status("api-health", f"{api}/health", 200),
            self._expect_status("api-readiness", f"{api}/ready", 200),
            self._expect_status("api-metrics", f"{api}/metrics", 200),
            self._expect_status(
                "anonymous-protected-api",
                f"{api}/api/v1/rsot/resource-taxonomy",
                401,
            ),
            self._expect_status("web-health", f"{web}/health", 200),
            self._expect_web_security_headers(f"{web}/"),
        )
        return results

    def assert_secure(self, api_base_url: str, web_base_url: str) -> tuple[HttpProbeResult, ...]:
        results = self.run(api_base_url, web_base_url)
        failures = [result.detail for result in results if not result.passed]
        if failures:
            raise SecurityHttpProbeError("; ".join(failures))
        return results

    def _expect_status(self, name: str, url: str, expected_status: int) -> HttpProbeResult:
        status, _headers = self._request(url)
        passed = status == expected_status
        return HttpProbeResult(
            name=name,
            passed=passed,
            detail=(
                f"{url} returned expected HTTP {expected_status}"
                if passed
                else f"{url} returned HTTP {status}, expected {expected_status}"
            ),
        )

    def _expect_web_security_headers(self, url: str) -> HttpProbeResult:
        status, headers = self._request(url)
        expected = {
            "x-content-type-options": "nosniff",
            "referrer-policy": "no-referrer",
        }
        failures = [
            f"{name}={headers.get(name, '<missing>')}"
            for name, value in expected.items()
            if headers.get(name, "").lower() != value
        ]
        if not headers.get("content-security-policy", "").strip():
            failures.append("content-security-policy=<missing>")
        passed = status == 200 and not failures
        return HttpProbeResult(
            name="web-security-headers",
            passed=passed,
            detail=(
                f"{url} exposes the required security headers"
                if passed
                else f"{url} security contract failed: {', '.join(failures)}"
            ),
        )

    def _request(self, url: str) -> tuple[int, dict[str, str]]:
        request = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                return int(response.status), {
                    key.lower(): value for key, value in response.headers.items()
                }
        except urllib.error.HTTPError as exc:
            return int(exc.code), {key.lower(): value for key, value in exc.headers.items()}


class SecurityHttpProbeCli:
    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(prog="security-http-probe")
        parser.add_argument("--api-base-url", required=True)
        parser.add_argument("--web-base-url", required=True)
        parser.add_argument("--timeout-seconds", type=float, default=10.0)
        args = parser.parse_args(argv)
        probe = SecurityHttpProbe(timeout_seconds=float(args.timeout_seconds))
        try:
            results = probe.assert_secure(str(args.api_base_url), str(args.web_base_url))
        except (SecurityHttpProbeError, OSError) as exc:
            print(f"security-http-probe: error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps([result.as_dict() for result in results], sort_keys=True))
        return 0


if __name__ == "__main__":
    raise SystemExit(SecurityHttpProbeCli.main())
