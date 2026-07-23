from pathlib import Path

from openinfra.quality.release_packaging import InstallerPackagingValidator


class TestReleasePackagingInstallerRollback:
    def test_all_installers_dry_run_and_restore_previous_content(self, tmp_path: Path) -> None:
        evidence = InstallerPackagingValidator().validate(Path.cwd(), tmp_path)

        dry_runs = evidence["dry_runs"]
        rollbacks = evidence["rollbacks"]
        assert isinstance(dry_runs, list)
        assert isinstance(rollbacks, list)
        assert len(dry_runs) == 6
        assert len(rollbacks) == 6
        assert all(item["transactional_rollback"] is True for item in dry_runs)
        assert all(item["count"] == 1 for item in rollbacks)
