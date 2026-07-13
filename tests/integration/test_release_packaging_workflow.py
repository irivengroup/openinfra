from pathlib import Path


class TestReleasePackagingWorkflow:
    def test_workflow_is_blocking_reproducible_and_signed(self) -> None:
        workflow = Path(".github/workflows/release-packaging.yml").read_text(encoding="utf-8")
        required = (
            "push:",
            "tags: ['v*']",
            "workflow_dispatch:",
            "actions/checkout@v6",
            "fetch-depth: 0",
            "actions/setup-python@v6",
            "actions/upload-artifact@v6",
            "git log -1 --pretty=%ct",
            "OPENINFRA_RELEASE_SIGNING_PRIVATE_KEY_B64",
            "scripts/release_packaging_audit.py",
            "--signing-key-from-env",
            "--enforce",
            "sha256sum --check",
            "ReleaseSignatureVerifier",
            "if-no-files-found: error",
            "retention-days: 90",
        )
        for fragment in required:
            assert fragment in workflow
        assert "pull_request_target:" not in workflow
        assert "--ephemeral-signing-key" not in workflow
