from __future__ import annotations

import pytest

from openinfra.domain.common import ValidationError
from openinfra.infrastructure.read_routing import (
    PostgreSQLReadRoutingSettings,
    PostgreSQLReplicaHealth,
    ReadConsistencyTokenCodec,
    ReadRoute,
    ReadRoutingContext,
)


def test_read_route_scope_is_nested_and_restored() -> None:
    assert ReadRoutingContext.current() is ReadRoute.PRIMARY
    with ReadRoutingContext.scope(ReadRoute.REPLICA):
        assert ReadRoutingContext.current() is ReadRoute.REPLICA
        with ReadRoutingContext.scope(ReadRoute.PRIMARY):
            assert ReadRoutingContext.current() is ReadRoute.PRIMARY
        assert ReadRoutingContext.current() is ReadRoute.REPLICA
    assert ReadRoutingContext.current() is ReadRoute.PRIMARY


def test_read_routing_settings_validate_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENINFRA_DB_MAX_REPLICA_LAG_SECONDS", "2.5")
    monkeypatch.setenv("OPENINFRA_DB_REPLICA_PROBE_INTERVAL_SECONDS", "3")
    monkeypatch.setenv("OPENINFRA_DB_READ_FALLBACK_TO_PRIMARY", "false")
    monkeypatch.setenv("OPENINFRA_DB_READ_REQUIRE_RECOVERY", "no")
    settings = PostgreSQLReadRoutingSettings.from_environment("postgresql:///replica")
    assert settings == PostgreSQLReadRoutingSettings(True, 2.5, 3.0, False, False)
    assert PostgreSQLReadRoutingSettings.from_environment("").enabled is False

    monkeypatch.setenv("OPENINFRA_DB_READ_ROUTING_ENABLED", "true")
    assert PostgreSQLReadRoutingSettings.from_environment("postgresql:///replica").enabled is True
    monkeypatch.setenv("OPENINFRA_DB_READ_ROUTING_ENABLED", "invalid")
    with pytest.raises(ValidationError, match="boolean"):
        PostgreSQLReadRoutingSettings.from_environment("postgresql:///replica")
    with pytest.raises(ValidationError, match="negative"):
        PostgreSQLReadRoutingSettings(True, -1, 1, True)
    with pytest.raises(ValidationError, match="positive"):
        PostgreSQLReadRoutingSettings(True, 1, 0, True)


def test_consistency_token_is_signed_short_lived_and_tamper_proof() -> None:
    now = [1_000.0]
    codec = ReadConsistencyTokenCodec("s" * 32, ttl_seconds=10, clock=lambda: now[0])
    token = codec.issue()
    assert codec.ttl_seconds == 10
    assert codec.validate(token) is True
    assert codec.validate(token + "x") is False
    assert codec.validate("") is False
    assert codec.validate("x" * 513) is False

    now[0] = 1_011.0
    assert codec.validate(token) is False
    with pytest.raises(ValidationError, match="32"):
        ReadConsistencyTokenCodec("short")
    with pytest.raises(ValidationError, match="between 1 and 300"):
        ReadConsistencyTokenCodec("s" * 32, ttl_seconds=301)


def test_replica_health_serialization_is_stable() -> None:
    assert PostgreSQLReplicaHealth.disabled().as_dict() == {
        "configured": False,
        "eligible": False,
        "is_replica": False,
        "lag_seconds": None,
        "checked_at_epoch": None,
        "detail": "read replica is not configured",
    }
