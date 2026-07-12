from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_compose_uses_idempotent_replication_and_transaction_pooling() -> None:
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))
    services = compose["services"]
    assert services["postgres-replica"]["depends_on"] == {
        "replication-bootstrap": {"condition": "service_completed_successfully"}
    }
    assert services["pgbouncer-primary"]["depends_on"]["postgres"]["condition"] == (
        "service_healthy"
    )
    assert (
        services["pgbouncer-replica"]["depends_on"]["postgres-replica"]["condition"]
        == "service_healthy"
    )
    api_environment = services["api"]["environment"]
    assert "@pgbouncer-primary:6432/" in api_environment["OPENINFRA_DATABASE_DSN"]
    assert "@pgbouncer-replica:6432/" in api_environment["OPENINFRA_DATABASE_READ_DSN"]
    assert api_environment["OPENINFRA_DB_READ_ROUTING_ENABLED"].endswith("-true}")
    assert "OPENINFRA_READ_CONSISTENCY_SECRET" in api_environment
    assert "OPENINFRA_CURSOR_SIGNING_SECRET" in api_environment

    pgbouncer = (ROOT / "docker/pgbouncer/entrypoint.sh").read_text(encoding="utf-8")
    assert "pool_mode = transaction" in pgbouncer
    assert "auth_type = scram-sha-256" in pgbouncer
    assert "max_prepared_statements = 0" in pgbouncer
    assert "server_reset_query_always = 1" in pgbouncer


def test_replica_bootstrap_scripts_are_idempotent_and_safe() -> None:
    bootstrap = (ROOT / "docker/postgresql/bootstrap-replication-role.sh").read_text(
        encoding="utf-8"
    )
    replica = (ROOT / "docker/postgresql/replica-entrypoint.sh").read_text(encoding="utf-8")
    assert "WHERE NOT EXISTS" in bootstrap
    assert "ALTER ROLE" in bootstrap
    assert "ON_ERROR_STOP=1" in bootstrap
    assert "pg_hba_file_rules" in bootstrap
    assert "pg_reload_conf" in bootstrap
    assert "scram-sha-256" in bootstrap
    assert "pg_basebackup" in replica
    assert "-R" in replica
    assert 'find "$PGDATA" -mindepth 1' in replica
    compose_text = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    assert "standby.signal" in compose_text
    assert "OPENINFRA_POSTGRES_REPLICATION_CIDR" in compose_text
    assert "openinfra-postgres-data:/var/lib/postgresql/data" in compose_text


def test_replication_bootstrap_configures_pg_hba_idempotently(
    tmp_path: Path,
) -> None:
    pgdata = tmp_path / "pgdata"
    pgdata.mkdir()
    hba_file = pgdata / "pg_hba.conf"
    hba_file.write_text(
        "local all all trust\nhost all all 0.0.0.0/0 scram-sha-256\n",
        encoding="utf-8",
    )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    pg_isready = bin_dir / "pg_isready"
    pg_isready.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    pg_isready.chmod(0o755)
    psql = bin_dir / "psql"
    psql.write_text(
        """#!/bin/sh
case "$*" in
  *":'replication_user'"*) printf '%s\n' "unexpected unexpanded psql variable" >&2; exit 2 ;;
  *"SHOW hba_file"*) printf '%s\n' "$FAKE_HBA_FILE" ;;
  *"SELECT pg_reload_conf()"*) printf 't\n' ;;
  *"SELECT count(*) FROM pg_hba_file_rules WHERE error IS NOT NULL"*) printf '0\n' ;;
  *"SELECT count(*) FROM pg_hba_file_rules"*)
      case "$*" in
        *"'openinfra_replica' = ANY(user_name)"*) printf '1\n' ;;
        *) printf '%s\n' "replication user literal missing from HBA verification" >&2; exit 2 ;;
      esac
      ;;
  *) cat >/dev/null || true ;;
esac
""",
        encoding="utf-8",
    )
    psql.chmod(0o755)

    environment = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "POSTGRES_DB": "openinfra",
        "POSTGRES_USER": "openinfra",
        "POSTGRES_PASSWORD": "primary-secret",
        "PGDATA": str(pgdata),
        "OPENINFRA_POSTGRES_REPLICATION_USER": "openinfra_replica",
        "OPENINFRA_POSTGRES_REPLICATION_PASSWORD": "replica-secret",
        "OPENINFRA_POSTGRES_REPLICATION_CIDR": "172.30.0.0/24",
        "FAKE_HBA_FILE": str(hba_file),
    }
    script = ROOT / "docker/postgresql/bootstrap-replication-role.sh"
    for _ in range(2):
        result = subprocess.run(
            [shutil.which("sh") or "/bin/sh", str(script)],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        assert result.returncode == 0, result.stderr

    configured = hba_file.read_text(encoding="utf-8")
    expected = "host replication openinfra_replica 172.30.0.0/24 scram-sha-256"
    assert configured.count(expected) == 1
    assert configured.splitlines()[1] == expected


def test_replication_bootstrap_rejects_unsafe_replication_user(
    tmp_path: Path,
) -> None:
    pgdata = tmp_path / "pgdata"
    pgdata.mkdir()
    (pgdata / "pg_hba.conf").write_text("local all all trust\n", encoding="utf-8")
    result = subprocess.run(
        [
            shutil.which("sh") or "/bin/sh",
            str(ROOT / "docker/postgresql/bootstrap-replication-role.sh"),
        ],
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "POSTGRES_DB": "openinfra",
            "POSTGRES_USER": "openinfra",
            "POSTGRES_PASSWORD": "primary-secret",
            "PGDATA": str(pgdata),
            "OPENINFRA_POSTGRES_REPLICATION_USER": "unsafe user",
            "OPENINFRA_POSTGRES_REPLICATION_PASSWORD": "replica-secret",
            "OPENINFRA_POSTGRES_REPLICATION_CIDR": "172.30.0.0/24",
        },
    )
    assert result.returncode == 64
    assert "unsupported pg_hba.conf characters" in result.stderr
