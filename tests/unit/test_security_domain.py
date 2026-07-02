from __future__ import annotations

from pathlib import Path

import pytest

from openinfra.application.security_services import (
    AuthenticateTokenCommand,
    BootstrapTokenCommand,
    ListTokensCommand,
    RevokeTokenCommand,
    RotateTokenCommand,
)
from openinfra.application.container import ApplicationFactory
from openinfra.domain.common import AccessDeniedError, ValidationError
from openinfra.domain.security import Permission


class TestSecurityDomainAndService:
    def test_bootstrap_token_hashes_secret_and_authenticates_principal(
        self,
        tmp_path: Path,
    ) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = "x" * 40
        result = app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="api-client-01",
                roles=("ipam:operator",),
                token=token,
            )
        )

        principal = app.security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id="default",
                token=token,
                required_permission=Permission.IPAM_ALLOCATE,
            )
        )

        assert "token" not in result.as_dict()
        assert result.token_prefix == token[:12]
        assert principal.subject == "api-client-01"
        assert Permission.IPAM_ALLOCATE in principal.permissions

    def test_generated_token_is_returned_once_and_secret_value_is_not_stored(
        self, tmp_path: Path
    ) -> None:
        data_path = tmp_path / "state.json"
        app = ApplicationFactory().create_json_application(data_path)
        result = app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="generated-client",
                roles=("viewer",),
            )
        )

        assert isinstance(result.token, str)
        assert len(result.token) >= 32
        assert result.token not in data_path.read_text(encoding="utf-8")

    def test_invalid_token_and_unsupported_role_are_rejected(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="viewer-client",
                roles=("viewer",),
                token="v" * 40,
            )
        )

        with pytest.raises(AccessDeniedError):
            app.security_service.authenticate_token(
                AuthenticateTokenCommand(
                    tenant_id="default",
                    token="w" * 40,
                    required_permission=Permission.SCHEMA_READ,
                )
            )
        with pytest.raises(AccessDeniedError):
            app.security_service.authenticate_token(
                AuthenticateTokenCommand(
                    tenant_id="default",
                    token="v" * 40,
                    required_permission=Permission.IPAM_ALLOCATE,
                )
            )
        with pytest.raises(ValidationError):
            app.security_service.bootstrap_token(
                BootstrapTokenCommand(
                    tenant_id="default",
                    actor="pytest",
                    subject="bad-role-client",
                    roles=("unsupported",),
                    token="z" * 40,
                )
            )

    def test_token_ttl_revoke_rotate_and_list_hide_secret_material(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        admin_token = "a" * 40
        ipam_token = "i" * 40
        rotated_token = "r" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="admin-client",
                roles=("admin",),
                token=admin_token,
                ttl_seconds=3600,
            )
        )
        ipam_result = app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="ipam-client",
                roles=("ipam:operator",),
                token=ipam_token,
                ttl_seconds=3600,
            )
        )

        page = app.security_service.list_tokens(
            ListTokensCommand(tenant_id="default", admin_token=admin_token, limit=10)
        )
        revoke_result = app.security_service.revoke_token(
            RevokeTokenCommand(
                tenant_id="default",
                actor="pytest",
                target_token=ipam_token,
                admin_token=admin_token,
            )
        )
        inactive_page = app.security_service.list_tokens(
            ListTokensCommand(
                tenant_id="default",
                admin_token=admin_token,
                limit=10,
                include_inactive=True,
            )
        )
        rotate_result = app.security_service.rotate_token(
            RotateTokenCommand(
                tenant_id="default",
                actor="pytest",
                current_token=admin_token,
                token=rotated_token,
                ttl_seconds=3600,
            )
        )

        assert ipam_result.expires_at is not None
        assert len(page.items) == 2
        assert all(item.token_hash not in item.as_public_dict().values() for item in page.items)
        assert revoke_result.revoked is True
        assert len(inactive_page.items) == 2
        assert any(item.revoked_at is not None for item in inactive_page.items)
        assert rotate_result.token_prefix == rotated_token[:12]
        with pytest.raises(AccessDeniedError):
            app.security_service.inspect_token("default", ipam_token)
        with pytest.raises(AccessDeniedError):
            app.security_service.inspect_token("default", admin_token)
        principal = app.security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id="default",
                token=rotated_token,
                required_permission=Permission.SECURITY_ADMIN,
            )
        )
        assert principal.subject == "admin-client"

    def test_token_ttl_and_pagination_cursor_are_validated(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = "a" * 40

        with pytest.raises(ValidationError):
            app.security_service.bootstrap_token(
                BootstrapTokenCommand(
                    tenant_id="default",
                    actor="pytest",
                    subject="short-ttl-client",
                    roles=("admin",),
                    token=token,
                    ttl_seconds=1,
                )
            )
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="page-client",
                roles=("admin",),
                token=token,
            )
        )
        with pytest.raises(ValidationError):
            app.security_service.list_tokens(
                ListTokensCommand(tenant_id="default", admin_token=token, limit=0)
            )
