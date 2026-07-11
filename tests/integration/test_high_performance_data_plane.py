from __future__ import annotations

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
    assert "pg_basebackup" in replica
    assert "-R" in replica
    assert 'find "$PGDATA" -mindepth 1' in replica
    assert "standby.signal" in (ROOT / "compose.yaml").read_text(encoding="utf-8")
