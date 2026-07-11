from __future__ import annotations

from collections.abc import Mapping, Sequence

import pytest

from openinfra.domain.common import OpenInfraError, ValidationError
from openinfra.infrastructure.postgresql import (
    ConnectionProtocol,
    CursorProtocol,
    PostgreSQLReplicaMonitor,
    PostgreSQLSessionRegistry,
)
from openinfra.infrastructure.read_routing import (
    PostgreSQLReadRoutingSettings,
    PostgreSQLReplicaHealth,
    ReadRoute,
    ReadRoutingContext,
)


class FakeCursor(CursorProtocol):
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection
        self.closed = False

    def execute(
        self,
        query: str,
        params: Mapping[str, object] | Sequence[object] | None = None,
    ) -> object:
        del params
        self.connection.queries.append(" ".join(query.split()))
        if self.connection.fail_probe:
            raise RuntimeError("replica unavailable")
        return None

    def fetchone(self) -> Mapping[str, object] | None:
        return {
            "is_replica": self.connection.is_replica,
            "lag_seconds": self.connection.lag_seconds,
        }

    def fetchall(self) -> Sequence[Mapping[str, object]]:
        return ()

    def close(self) -> None:
        self.closed = True


class FakeConnection(ConnectionProtocol):
    def __init__(
        self,
        source: str,
        *,
        is_replica: bool = False,
        lag_seconds: float | None = 0.0,
        fail_probe: bool = False,
    ) -> None:
        self.source = source
        self.is_replica = is_replica
        self.lag_seconds = lag_seconds
        self.fail_probe = fail_probe
        self.queries: list[str] = []
        self.rollbacks = 0
        self.closed = False

    def cursor(self) -> CursorProtocol:
        return FakeCursor(self)

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


class FakeFactory:
    def __init__(self, source: str, **connection_options: object) -> None:
        self.source = source
        self.connection_options = connection_options
        self.created: list[FakeConnection] = []
        self.released: list[FakeConnection] = []
        self.closed = False

    def create(self) -> FakeConnection:
        connection = FakeConnection(self.source, **self.connection_options)
        self.created.append(connection)
        return connection

    def release(self, connection: ConnectionProtocol) -> None:
        assert isinstance(connection, FakeConnection)
        self.released.append(connection)

    def close(self) -> None:
        self.closed = True


class StaticMonitor:
    def __init__(self, health: PostgreSQLReplicaHealth) -> None:
        self.health = health
        self.force_values: list[bool] = []

    def snapshot(self, *, force: bool = False) -> PostgreSQLReplicaHealth:
        self.force_values.append(force)
        return self.health


def _settings(*, fallback: bool = True) -> PostgreSQLReadRoutingSettings:
    return PostgreSQLReadRoutingSettings(True, 5, 2, fallback)


def test_registry_routes_read_scope_to_healthy_replica_and_tracks_metrics() -> None:
    primary = FakeFactory("primary")
    replica = FakeFactory("replica")
    monitor = StaticMonitor(PostgreSQLReplicaHealth(True, True, True, 0.25, 1_000.0, "eligible"))
    registry = PostgreSQLSessionRegistry(
        primary,
        replica,
        _settings(),
        monitor,  # type: ignore[arg-type]
    )

    with ReadRoutingContext.scope(ReadRoute.REPLICA), registry.read_scope() as connection:
        assert isinstance(connection, FakeConnection)
        assert connection.source == "replica"
        assert registry.current() is connection
    assert registry.has_current() is False
    assert replica.released[0].rollbacks == 1

    status = registry.routing_status_as_dict(force_probe=True)
    assert status["counters"] == {
        "primary_acquisitions": 0,
        "replica_acquisitions": 1,
        "replica_fallbacks": 0,
    }
    assert monitor.force_values[-1] is True
    registry.close()
    assert primary.closed is replica.closed is True


def test_registry_falls_back_or_fails_when_replica_is_not_eligible() -> None:
    health = PostgreSQLReplicaHealth(True, False, True, 30.0, 1_000.0, "lagged")
    primary = FakeFactory("primary")
    replica = FakeFactory("replica")
    registry = PostgreSQLSessionRegistry(
        primary,
        replica,
        _settings(fallback=True),
        StaticMonitor(health),  # type: ignore[arg-type]
    )
    with ReadRoutingContext.scope(ReadRoute.REPLICA), registry.read_scope() as connection:
        assert isinstance(connection, FakeConnection)
        assert connection.source == "primary"
    assert registry.routing_status_as_dict()["counters"] == {
        "primary_acquisitions": 1,
        "replica_acquisitions": 0,
        "replica_fallbacks": 1,
    }

    strict = PostgreSQLSessionRegistry(
        FakeFactory("primary"),
        FakeFactory("replica"),
        _settings(fallback=False),
        StaticMonitor(health),  # type: ignore[arg-type]
    )
    with (
        ReadRoutingContext.scope(ReadRoute.REPLICA),
        pytest.raises(OpenInfraError, match="not eligible"),
        strict.read_scope(),
    ):
        pass


def test_registry_keeps_primary_for_write_route_and_reuses_bound_connection() -> None:
    primary = FakeFactory("primary")
    replica = FakeFactory("replica")
    registry = PostgreSQLSessionRegistry(
        primary,
        replica,
        _settings(),
        StaticMonitor(PostgreSQLReplicaHealth(True, True, True, 0.1, 1.0, "ok")),  # type: ignore[arg-type]
    )
    with registry.read_scope() as outer, registry.read_scope() as inner:
        assert inner is outer
    assert len(primary.created) == 1
    assert not replica.created


def test_replica_monitor_caches_probe_and_reports_all_failure_modes() -> None:
    monotonic = [0.0]
    factory = FakeFactory("replica", is_replica=True, lag_seconds=0.5)
    monitor = PostgreSQLReplicaMonitor(
        factory,  # type: ignore[arg-type]
        _settings(),
        monotonic_clock=lambda: monotonic[0],
        epoch_clock=lambda: 42.0,
    )
    first = monitor.snapshot()
    second = monitor.snapshot()
    assert first.eligible is second.eligible is True
    assert len(factory.created) == 1
    monotonic[0] = 3.0
    assert monitor.snapshot().eligible is True
    assert len(factory.created) == 2

    for options, expected in (
        ({"is_replica": False, "lag_seconds": 0.1}, "not a PostgreSQL standby"),
        ({"is_replica": True, "lag_seconds": None}, "timestamp is unavailable"),
        ({"is_replica": True, "lag_seconds": 8.0}, "exceeds threshold"),
        ({"is_replica": True, "lag_seconds": 0.0, "fail_probe": True}, "probe failed"),
    ):
        snapshot = PostgreSQLReplicaMonitor(
            FakeFactory("replica", **options),  # type: ignore[arg-type]
            _settings(),
        ).snapshot(force=True)
        assert snapshot.eligible is False
        assert expected in snapshot.detail


def test_registry_rejects_enabled_routing_without_read_factory() -> None:
    with pytest.raises(ValidationError, match="requires a read connection factory"):
        PostgreSQLSessionRegistry(FakeFactory("primary"), read_routing_settings=_settings())
