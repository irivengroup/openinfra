from pathlib import Path


class TestReleaseSecurityWorkflow:
    def test_release_security_workflow_is_blocking_and_complete(self) -> None:
        workflow = Path(".github/workflows/release-security.yml").read_text(encoding="utf-8")

        required = (
            "push:",
            "tags: ['v*']",
            "workflow_dispatch:",
            "actions/checkout@v6",
            "actions/setup-python@v6",
            "actions/setup-node@v6",
            "actions/upload-artifact@v6",
            "python scripts/docker_environment.py init",
            "docker compose --env-file .env build api",
            "docker compose --env-file .env up -d postgres migrate auth-bootstrap api web",
            "scripts/release_security_audit.py",
            "--image-ref",
            "--api-base-url",
            "--web-base-url",
            "--enforce",
            "retention-days: 90",
            "down --volumes --remove-orphans",
            "if: steps.security-audit.outcome != 'success'",
        )
        for fragment in required:
            assert fragment in workflow
        assert "pull_request_target:" not in workflow
        assert "actions/checkout@v4" not in workflow
        assert "actions/setup-python@v5" not in workflow
