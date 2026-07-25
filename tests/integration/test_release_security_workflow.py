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
            "OPENINFRA_DB_READ_ROUTING_ENABLED: 'false'",
            "postgres runtime-secrets migrate pgbouncer-primary auth-bootstrap api web",
            "docker compose --env-file .env ps --all",
            "docker compose --env-file .env logs --no-color --tail=300",
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
        assert "pgbouncer-replica" not in workflow.split(
            "- name: Start live DAST topology", 1
        )[1].split("- name: Execute blocking release security audit", 1)[0]
