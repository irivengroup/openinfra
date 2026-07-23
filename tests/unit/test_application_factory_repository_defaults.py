from __future__ import annotations

from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.infrastructure.async_processing import JsonAsyncProcessingRepository
from openinfra.infrastructure.json_store import (
    JsonAccessPolicyRepository,
    JsonAuditRepository,
    JsonDcimRepository,
    JsonDocumentStore,
    JsonIdentityRepository,
    JsonIpamRepository,
    JsonReadinessProbe,
    JsonSchemaStatusProvider,
    JsonSecurityRepository,
    JsonTransactionManager,
)


class TestApplicationFactoryRepositoryDefaults:
    def test_build_application_selects_json_adapters_from_document_store(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        store = JsonDocumentStore(tmp_path / "state.json")
        monkeypatch.setenv("OPENINFRA_ARTIFACT_ROOT", str(tmp_path / "artifacts"))

        application = ApplicationFactory()._build_application(
            store=store,
            dcim_repository=JsonDcimRepository(store),
            ipam_repository=JsonIpamRepository(store),
            audit_repository=JsonAuditRepository(store),
            security_repository=JsonSecurityRepository(store),
            identity_repository=JsonIdentityRepository(store),
            access_policy_repository=JsonAccessPolicyRepository(store),
            transaction_manager=JsonTransactionManager(store),
            readiness_probe=JsonReadinessProbe(store),
            schema_status_provider=JsonSchemaStatusProvider(),
            edition="lite",
        )

        assert application.store is store
        assert isinstance(application.async_processing_repository, JsonAsyncProcessingRepository)
        assert application.artifact_store.root == tmp_path / "artifacts"
        assert application.source_of_truth_repository is not None
        assert application.source_governance_repository is not None
        assert application.itam_support_repository is not None
