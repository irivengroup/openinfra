from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from openinfra.interfaces.cli import OpenInfraCLI


def test_cli_database_handlers_and_additional_identity_sot_paths(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    cli = OpenInfraCLI()

    class FakeStatus:
        def as_dict(self):
            return {"ready": True, "pending": []}

    class FakeExecutor:
        def status_as_dict(self):
            return {"ready": True, "pending": []}

        def apply_all(self, dry_run=False):
            assert dry_run is True
            return FakeStatus()

    monkeypatch.setattr(cli, "_create_migration_executor", lambda args: FakeExecutor())
    assert cli._handle_database_status(Namespace()) == 0
    assert cli._handle_database_apply_migrations(Namespace(dry_run=True)) == 0
    captured = capsys.readouterr()
    assert "ready" in captured.out

    data = tmp_path / "state.json"
    admin_token = "t" * 40
    assert (
        cli.run(
            [
                "security",
                "bootstrap-token",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--subject",
                "admin-cli",
                "--token",
                admin_token,
                "--role",
                "admin",
            ]
        )
        == 0
    )
    assert (
        cli.run(
            [
                "identity",
                "create-user",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                admin_token,
                "--username",
                "cli-user",
                "--display-name",
                "CLI User",
                "--email",
                "cli-user@example.org",
                "--role",
                "viewer",
            ]
        )
        == 0
    )
    assert (
        cli.run(
            [
                "identity",
                "create-group",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                admin_token,
                "--name",
                "cli-group",
                "--display-name",
                "CLI Group",
                "--role",
                "sot:reader",
            ]
        )
        == 0
    )
    assert (
        cli.run(
            [
                "identity",
                "grant-user-role",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                admin_token,
                "--username",
                "cli-user",
                "--role",
                "dcim:operator",
            ]
        )
        == 0
    )
    assert (
        cli.run(
            [
                "identity",
                "grant-group-role",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                admin_token,
                "--group",
                "cli-group",
                "--role",
                "ipam:operator",
            ]
        )
        == 0
    )
    assert (
        cli.run(
            [
                "sot",
                "upsert-object",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                admin_token,
                "--key",
                "device/cli-srv",
                "--kind",
                "device",
                "--display-name",
                "CLI Server",
                "--source",
                "manual",
            ]
        )
        == 0
    )
    assert (
        cli.run(
            [
                "sot",
                "get-object",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                admin_token,
                "--key",
                "device/cli-srv",
            ]
        )
        == 0
    )
