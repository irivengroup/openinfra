from __future__ import annotations

import json
from pathlib import Path

from openinfra.interfaces.cli import OpenInfraCLI


class TestOpenInfraCli:
    def test_version_command(self, capsys: object) -> None:
        code = OpenInfraCLI().run(["version"])
        captured = capsys.readouterr()

        assert code == 0
        assert captured.out.strip() == "0.9.0"

    def test_spec_validate_command(self, capsys: object) -> None:
        root = Path("docs/specifications/OpenInfra-CDC-SFG-STG-v4")

        code = OpenInfraCLI().run(["spec", "validate", "--root", str(root)])
        captured = capsys.readouterr()

        assert code == 0
        assert "status=valid" in captured.out
        assert "version=4.0.0" in captured.out

    def test_database_render_migration_command(self, capsys: object) -> None:
        code = OpenInfraCLI().run([
            "database",
            "render-migration",
            "--name",
            "0001_bootstrap",
            "--root",
            "migrations/postgresql",
        ])
        captured = capsys.readouterr()

        assert code == 0
        assert "PARTITION BY" in captured.out
        assert "CREATE INDEX" in captured.out

    def test_database_status_requires_postgresql_dsn(self, capsys: object) -> None:
        code = OpenInfraCLI().run([
            "database",
            "status",
            "--root",
            "migrations/postgresql",
        ])
        captured = capsys.readouterr()

        assert code == 2
        assert "OPENINFRA_DATABASE_DSN" in captured.err


    def test_security_bootstrap_and_whoami_commands(self, tmp_path: Path, capsys: object) -> None:
        data = tmp_path / "state.json"
        token = "s" * 40
        create_code = OpenInfraCLI().run([
            "security",
            "bootstrap-token",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--subject",
            "cli-client",
            "--role",
            "ipam:operator",
            "--token",
            token,
        ])
        created = json.loads(capsys.readouterr().out)
        whoami_code = OpenInfraCLI().run([
            "security",
            "whoami",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--token",
            token,
        ])
        principal = json.loads(capsys.readouterr().out)

        assert create_code == 0
        assert whoami_code == 0
        assert "token" not in created
        assert created["token_prefix"] == token[:12]
        assert principal["subject"] == "cli-client"
        assert "ipam.allocate" in principal["permissions"]

    def test_ipam_allocate_command(self, tmp_path: Path, capsys: object) -> None:
        data = tmp_path / "state.json"
        code = OpenInfraCLI().run([
            "ipam",
            "allocate",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--vrf",
            "default",
            "--prefix",
            "10.6.0.0/30",
            "--hostname",
            "srv01",
            "--idempotency-key",
            "req-1",
        ])
        captured = capsys.readouterr()
        payload = json.loads(captured.out)

        assert code == 0
        assert payload["address"] == "10.6.0.1"
        assert payload["created"] is True

    def test_dcim_locate_command(self, tmp_path: Path, capsys: object) -> None:
        data = tmp_path / "state.json"
        code = OpenInfraCLI().run([
            "dcim",
            "locate",
            "--data",
            str(data),
            "--asset-tag",
            "SRV-CLI-1",
            "--equipment-name",
            "CLI server",
            "--site",
            "PAR1",
            "--building",
            "BAT-A",
            "--room",
            "MMR1",
            "--row",
            "B",
            "--column",
            "12",
            "--rack",
            "R42",
            "--u-position",
            "18",
        ])
        captured = capsys.readouterr()

        assert code == 0
        assert "site=PAR1" in captured.out
        assert "row=B" in captured.out
        assert "column=12" in captured.out

    def test_security_lifecycle_commands(self, tmp_path: Path, capsys: object) -> None:
        data = tmp_path / "state.json"
        admin_token = "a" * 40
        worker_token = "w" * 40
        rotated_token = "r" * 40
        OpenInfraCLI().run([
            "security",
            "bootstrap-token",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--subject",
            "admin-client",
            "--role",
            "admin",
            "--token",
            admin_token,
            "--ttl-seconds",
            "3600",
        ])
        capsys.readouterr()
        OpenInfraCLI().run([
            "security",
            "bootstrap-token",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--subject",
            "worker-client",
            "--role",
            "viewer",
            "--token",
            worker_token,
        ])
        capsys.readouterr()

        list_code = OpenInfraCLI().run([
            "security",
            "list-tokens",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--admin-token",
            admin_token,
            "--limit",
            "10",
        ])
        listed = json.loads(capsys.readouterr().out)
        revoke_code = OpenInfraCLI().run([
            "security",
            "revoke-token",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--target-token",
            worker_token,
            "--admin-token",
            admin_token,
        ])
        revoked = json.loads(capsys.readouterr().out)
        rotate_code = OpenInfraCLI().run([
            "security",
            "rotate-token",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--current-token",
            admin_token,
            "--token",
            rotated_token,
        ])
        rotated = json.loads(capsys.readouterr().out)

        assert list_code == 0
        assert len(listed["items"]) == 2
        assert "token_hash" not in json.dumps(listed)
        assert revoke_code == 0
        assert revoked["revoked"] is True
        assert rotate_code == 0
        assert rotated["token_prefix"] == rotated_token[:12]

    def test_database_render_security_lifecycle_migration_command(self, capsys: object) -> None:
        code = OpenInfraCLI().run([
            "database",
            "render-migration",
            "--name",
            "0003_security_token_lifecycle",
            "--root",
            "migrations/postgresql",
        ])
        captured = capsys.readouterr()

        assert code == 0
        assert "ALTER TABLE api_tokens" in captured.out
        assert "idx_api_tokens_lifecycle_active" in captured.out

    def test_identity_cli_lifecycle(self, tmp_path: Path, capsys: object) -> None:
        data = tmp_path / "state.json"
        admin_token = "i" * 40
        OpenInfraCLI().run([
            "security",
            "bootstrap-token",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--subject",
            "identity-admin",
            "--role",
            "admin",
            "--token",
            admin_token,
        ])
        capsys.readouterr()
        create_user_code = OpenInfraCLI().run([
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
            "cli-user@example.com",
            "--role",
            "viewer",
        ])
        user = json.loads(capsys.readouterr().out)
        create_group_code = OpenInfraCLI().run([
            "identity",
            "create-group",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--admin-token",
            admin_token,
            "--name",
            "cli-ipam",
            "--display-name",
            "CLI IPAM",
            "--role",
            "ipam:operator",
        ])
        group = json.loads(capsys.readouterr().out)
        add_code = OpenInfraCLI().run([
            "identity",
            "add-user-to-group",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--admin-token",
            admin_token,
            "--username",
            "cli-user",
            "--group",
            "cli-ipam",
        ])
        membership = json.loads(capsys.readouterr().out)
        effective_code = OpenInfraCLI().run([
            "identity",
            "effective",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--admin-token",
            admin_token,
            "--subject",
            "cli-user",
        ])
        effective = json.loads(capsys.readouterr().out)

        assert create_user_code == 0
        assert create_group_code == 0
        assert add_code == 0
        assert effective_code == 0
        assert user["email"] == "cli-user@example.com"
        assert group["roles"] == ["ipam:operator"]
        assert membership["group_name"] == "cli-ipam"
        assert effective["effective_roles"] == ["ipam:operator", "viewer"]

    def test_database_render_identity_migration_command(self, capsys: object) -> None:
        code = OpenInfraCLI().run([
            "database",
            "render-migration",
            "--name",
            "0004_identity_users_groups",
            "--root",
            "migrations/postgresql",
        ])
        captured = capsys.readouterr()

        assert code == 0
        assert "identity_users" in captured.out
        assert "idx_audit_events_identity_actions" in captured.out

class TestOpenInfraAccessPolicyCli:
    def test_access_policy_cli_lifecycle_and_authenticated_ipam(
        self, tmp_path: Path, capsys: object
    ) -> None:
        data = tmp_path / "state.json"
        admin_token = "m" * 40
        worker_token = "n" * 40
        OpenInfraCLI().run([
            "security",
            "bootstrap-token",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--subject",
            "admin-client",
            "--role",
            "admin",
            "--token",
            admin_token,
        ])
        capsys.readouterr()
        OpenInfraCLI().run([
            "security",
            "bootstrap-token",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--subject",
            "worker-client",
            "--role",
            "ipam:operator",
            "--token",
            worker_token,
        ])
        capsys.readouterr()

        create_code = OpenInfraCLI().run([
            "access",
            "create-rule",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--admin-token",
            admin_token,
            "--name",
            "worker-par1-prod",
            "--permission",
            "ipam.allocate",
            "--effect",
            "allow",
            "--subject",
            "worker-client",
            "--site-code",
            "PAR1",
            "--environment",
            "prod",
        ])
        rule = json.loads(capsys.readouterr().out)
        list_code = OpenInfraCLI().run([
            "access",
            "list-rules",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--admin-token",
            admin_token,
        ])
        rules = json.loads(capsys.readouterr().out)
        evaluate_code = OpenInfraCLI().run([
            "access",
            "evaluate",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--token",
            worker_token,
            "--permission",
            "ipam.allocate",
            "--site-code",
            "PAR1",
            "--environment",
            "prod",
        ])
        allowed = json.loads(capsys.readouterr().out)
        ipam_code = OpenInfraCLI().run([
            "ipam",
            "allocate",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--auth-token",
            worker_token,
            "--site-code",
            "PAR1",
            "--environment",
            "prod",
            "--vrf",
            "default",
            "--prefix",
            "10.9.0.0/30",
            "--hostname",
            "srv-abac",
            "--idempotency-key",
            "abac-req-1",
        ])
        allocation = json.loads(capsys.readouterr().out)
        denied_code = OpenInfraCLI().run([
            "ipam",
            "allocate",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--auth-token",
            worker_token,
            "--site-code",
            "LON1",
            "--environment",
            "prod",
            "--vrf",
            "default",
            "--prefix",
            "10.9.0.0/30",
            "--hostname",
            "srv-denied",
            "--idempotency-key",
            "abac-req-2",
        ])
        denied = capsys.readouterr()
        deactivate_code = OpenInfraCLI().run([
            "access",
            "deactivate-rule",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--admin-token",
            admin_token,
            "--name",
            "worker-par1-prod",
        ])
        deactivated = json.loads(capsys.readouterr().out)

        assert create_code == 0
        assert rule["name"] == "worker-par1-prod"
        assert list_code == 0
        assert rules["items"][0]["permission"] == "ipam.allocate"
        assert evaluate_code == 0
        assert allowed["allowed"] is True
        assert ipam_code == 0
        assert allocation["address"] == "10.9.0.1"
        assert denied_code == 2
        assert "access policy denies" in denied.err
        assert deactivate_code == 0
        assert deactivated["deactivated"] is True

    def test_database_render_access_policy_migration_command(self, capsys: object) -> None:
        code = OpenInfraCLI().run([
            "database",
            "render-migration",
            "--name",
            "0005_access_policy_abac",
            "--root",
            "migrations/postgresql",
        ])
        captured = capsys.readouterr()

        assert code == 0
        assert "CREATE TABLE IF NOT EXISTS access_policy_rules" in captured.out
        assert "idx_audit_events_access_policy" in captured.out

    def test_audit_cli_list_export_and_verify_integrity(
        self, tmp_path: Path, capsys: object
    ) -> None:
        data = tmp_path / "state.json"
        admin_token = "h" * 40
        OpenInfraCLI().run([
            "security",
            "bootstrap-token",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--subject",
            "audit-admin",
            "--role",
            "admin",
            "--token",
            admin_token,
        ])
        capsys.readouterr()
        OpenInfraCLI().run([
            "ipam",
            "allocate",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--vrf",
            "default",
            "--prefix",
            "10.99.0.0/30",
            "--hostname",
            "audit-srv",
            "--idempotency-key",
            "audit-req-1",
        ])
        capsys.readouterr()

        list_code = OpenInfraCLI().run([
            "audit",
            "list",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--admin-token",
            admin_token,
            "--limit",
            "10",
        ])
        listed = json.loads(capsys.readouterr().out)
        export_code = OpenInfraCLI().run([
            "audit",
            "export",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--admin-token",
            admin_token,
            "--format",
            "jsonl",
            "--limit",
            "10",
        ])
        exported = json.loads(capsys.readouterr().out)
        verify_code = OpenInfraCLI().run([
            "audit",
            "verify-integrity",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--admin-token",
            admin_token,
        ])
        verified = json.loads(capsys.readouterr().out)

        assert list_code == 0
        assert export_code == 0
        assert verify_code == 0
        assert listed["items"]
        assert listed["items"][0]["record_hash"]
        assert "token_hash" not in json.dumps(listed)
        assert exported["content_type"] == "application/x-ndjson"
        assert exported["count"] >= 1
        assert verified["valid"] is True

    def test_database_render_audit_integrity_migration_command(self, capsys: object) -> None:
        code = OpenInfraCLI().run([
            "database",
            "render-migration",
            "--name",
            "0006_audit_trail_integrity",
            "--root",
            "migrations/postgresql",
        ])
        captured = capsys.readouterr()

        assert code == 0
        assert "previous_hash" in captured.out
        assert "idx_audit_events_integrity_chain" in captured.out
