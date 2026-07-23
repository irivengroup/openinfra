from __future__ import annotations

import json
import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta

import pytest

from openinfra.domain.common import ConflictError
from openinfra.domain.licensing import (
    InstallationIdentity,
    LicenseEntitlement,
    LicenseStateCorruptedError,
)
from openinfra.infrastructure.licensing import Ed25519LicenseCryptography
from openinfra.infrastructure.postgresql import (
    ConnectionProtocol,
    CursorProtocol,
    PostgreSQLClusterProfile,
    PostgreSQLConnectionFactory,
    PostgreSQLLicenseRepository,
    PostgreSQLSessionRegistry,
    PostgreSQLTransactionManager,
)


class LicenseCursor(CursorProtocol):
    def __init__(self, connection: LicenseConnection) -> None:
        self._connection = connection
        self._row: Mapping[str, object] | None = None
        self.rowcount = -1
        self.closed = False

    def execute(
        self,
        query: str,
        params: Mapping[str, object] | Sequence[object] | None = None,
    ) -> object:
        effective = dict(params or {})
        normalized = " ".join(query.split())
        self._connection.statements.append((normalized, effective))
        self._row = None
        self.rowcount = -1

        if normalized.startswith("SELECT identity, entitlement, activated_at, last_seen_at"):
            self._row = None if self._connection.state is None else dict(self._connection.state)
        elif normalized.startswith("SELECT identity FROM runtime_license_state"):
            if self._connection.state is not None:
                self._row = {"identity": self._connection.state["identity"]}
                self._connection.lock_count += 1
        elif normalized.startswith("INSERT INTO runtime_license_state"):
            if self._connection.state is None:
                self._connection.state = {
                    "identity": str(effective["identity"]),
                    "entitlement": None,
                    "activated_at": None,
                    "last_seen_at": None,
                }
                self.rowcount = 1
            else:
                self.rowcount = 0
        elif normalized.startswith("UPDATE runtime_license_state SET entitlement"):
            if self._connection.state is None:
                self.rowcount = 0
            else:
                self._connection.state.update(
                    {
                        "entitlement": str(effective["entitlement"]),
                        "activated_at": effective["activated_at"],
                        "last_seen_at": effective["last_seen_at"],
                    }
                )
                self.rowcount = 1
        elif normalized.startswith("UPDATE runtime_license_state SET last_seen_at"):
            state = self._connection.state
            if state is None:
                self.rowcount = 0
            else:
                identity = json.loads(str(state["identity"]))
                if identity["installation_id"] != effective["installation_id"]:
                    self.rowcount = 0
                else:
                    state["last_seen_at"] = effective["last_seen_at"]
                    self.rowcount = 1
        else:
            raise AssertionError(f"unexpected SQL in licensing repository test: {normalized}")
        return self

    def fetchone(self) -> Mapping[str, object] | None:
        return self._row

    def fetchall(self) -> Sequence[Mapping[str, object]]:
        return () if self._row is None else (self._row,)

    def close(self) -> object:
        self.closed = True
        return None


class LicenseConnection(ConnectionProtocol):
    def __init__(self) -> None:
        self.state: dict[str, object] | None = None
        self.statements: list[tuple[str, dict[str, object]]] = []
        self.lock_count = 0
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self) -> CursorProtocol:
        return LicenseCursor(self)

    def commit(self) -> object:
        self.commits += 1
        return None

    def rollback(self) -> object:
        self.rollbacks += 1
        return None

    def close(self) -> object:
        self.closed = True
        return None


class LicenseConnector:
    def __init__(self) -> None:
        self.connection = LicenseConnection()

    def connect(self, _dsn: str, _profile: PostgreSQLClusterProfile) -> ConnectionProtocol:
        return self.connection


def _runtime() -> tuple[
    PostgreSQLLicenseRepository,
    PostgreSQLTransactionManager,
    LicenseConnection,
    InstallationIdentity,
    LicenseEntitlement,
]:
    connector = LicenseConnector()
    registry = PostgreSQLSessionRegistry(
        PostgreSQLConnectionFactory(
            "postgresql://openinfra@db/openinfra",
            connector=connector.connect,
        )
    )
    repository = PostgreSQLLicenseRepository(registry)
    transaction_manager = PostgreSQLTransactionManager(registry)
    crypto = Ed25519LicenseCryptography()
    identity, request, _private_key = crypto.create_installation_material(
        installation_id=str(uuid.uuid4()),
        license_id=str(uuid.uuid4()),
        company_name="OpenInfra PostgreSQL Customer",
        edition="enterprise",
        requested_max_hosts=250,
    )
    authority_private, _authority_public, _authority_key_id = crypto.generate_authority_material(
        b"postgresql repository test authority password"
    )
    now = datetime(2026, 7, 20, 12, tzinfo=UTC)
    entitlement = crypto.issue_entitlement(
        request=request,
        authority_private_key_pem=authority_private,
        password=b"postgresql repository test authority password",
        max_hosts=250,
        issued_at=now,
        not_before=now,
        expires_at=now + timedelta(days=365),
    )
    return repository, transaction_manager, connector.connection, identity, entitlement


def test_postgresql_license_repository_persists_locks_and_updates_state() -> None:
    repository, transaction_manager, connection, identity, entitlement = _runtime()
    now = datetime(2026, 7, 20, 12, tzinfo=UTC)

    with transaction_manager.begin() as unit_of_work:
        assert repository.get_state() is None
        repository.save_identity(identity)
        repository.lock_state(identity.installation_id)
        repository.save_activation(entitlement, now, now)
        repository.update_last_seen(identity.installation_id, now + timedelta(hours=2))
        restored = repository.get_state()
        unit_of_work.commit()

    assert restored is not None
    assert restored.identity == identity
    assert restored.entitlement == entitlement
    assert restored.activated_at == now
    assert restored.last_seen_at == now + timedelta(hours=2)
    assert connection.lock_count == 1
    assert connection.commits == 1
    assert any("FOR UPDATE" in query for query, _params in connection.statements)


def test_postgresql_license_repository_preserves_immutable_identity() -> None:
    repository, transaction_manager, _connection, identity, _entitlement = _runtime()
    crypto = Ed25519LicenseCryptography()
    other_identity, _request, _private = crypto.create_installation_material(
        installation_id=str(uuid.uuid4()),
        license_id=str(uuid.uuid4()),
        company_name="Different Customer",
        edition="enterprise",
        requested_max_hosts=50,
    )

    with transaction_manager.begin():
        repository.save_identity(identity)

    with (
        pytest.raises(ConflictError, match="immutable installation identity"),
        transaction_manager.begin(),
    ):
        repository.save_identity(other_identity)


def test_postgresql_license_repository_fails_closed_on_missing_or_corrupted_state() -> None:
    repository, transaction_manager, connection, identity, entitlement = _runtime()
    now = datetime(2026, 7, 20, 12, tzinfo=UTC)

    with (
        pytest.raises(LicenseStateCorruptedError, match="identity is missing"),
        transaction_manager.begin(),
    ):
        repository.save_activation(entitlement, now, now)

    with (
        pytest.raises(LicenseStateCorruptedError, match="identity is missing"),
        transaction_manager.begin(),
    ):
        repository.update_last_seen(identity.installation_id, now)

    connection.state = {
        "identity": "not-json",
        "entitlement": None,
        "activated_at": None,
        "last_seen_at": None,
    }
    with (
        pytest.raises(LicenseStateCorruptedError, match="state is invalid"),
        transaction_manager.begin(),
    ):
        repository.get_state()

    connection.state = {
        "identity": json.dumps(identity.as_dict()),
        "entitlement": json.dumps(entitlement.as_dict()),
        "activated_at": "not-a-date",
        "last_seen_at": None,
    }
    with (
        pytest.raises(LicenseStateCorruptedError, match="state is invalid"),
        transaction_manager.begin(),
    ):
        repository.get_state()
