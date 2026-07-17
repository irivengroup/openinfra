from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

import httpx
import pytest

from openinfra.domain.common import AccessDeniedError, ValidationError
from openinfra.domain.federated_identity import TeamSyncSourceConfig
from openinfra.infrastructure.advanced_identity import (
    AuthProxyTeamSyncSource,
    OAuthTeamSyncSource,
)


class _SecretResolver:
    def __init__(self, value: str) -> None:
        self.value = value

    def resolve(self, reference: str) -> str:
        assert reference
        return self.value


class TestAdvancedIdentityAdapters:
    def test_oauth_pagination_remains_on_configured_origin(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/sync" and "page" not in request.url.params:
                return httpx.Response(
                    200,
                    json={
                        "users": [{"subject": "alice", "display_name": "Alice"}],
                        "groups": [],
                        "next": "/sync?page=2",
                    },
                )
            return httpx.Response(
                200,
                json={
                    "users": [{"subject": "bob", "display_name": "Bob"}],
                    "groups": [
                        {
                            "name": "Operators",
                            "members": ["alice", "bob"],
                            "roles": ["operator"],
                        }
                    ],
                },
            )

        config = TeamSyncSourceConfig.create(
            tenant_id="default",
            source_id="oauth-main",
            provider="oauth",
            endpoint="https://identity.example.net/sync",
            token_ref="file:///token",  # noqa: S106
        )
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            snapshot = OAuthTeamSyncSource(_SecretResolver("token"), client).fetch(config)

        assert tuple(user.subject for user in snapshot.users) == ("alice", "bob")
        assert snapshot.groups[0].members == ("alice", "bob")

    def test_oauth_rejects_cross_origin_pagination(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            del request
            return httpx.Response(
                200,
                json={"users": [], "groups": [], "next": "https://evil.example/sync"},
            )

        config = TeamSyncSourceConfig.create(
            tenant_id="default",
            source_id="oauth-main",
            provider="oauth",
            endpoint="https://identity.example.net/sync",
            token_ref="file:///token",  # noqa: S106
        )
        with (
            httpx.Client(transport=httpx.MockTransport(handler)) as client,
            pytest.raises(ValidationError, match="configured HTTPS origin"),
        ):
            OAuthTeamSyncSource(_SecretResolver("token"), client).fetch(config)

    def test_auth_proxy_requires_valid_hmac_and_rejects_symlink(self, tmp_path: Path) -> None:
        payload = {
            "users": [{"subject": "alice", "display_name": "Alice"}],
            "groups": [
                {
                    "name": "Operators",
                    "roles": ["operator"],
                    "members": ["alice"],
                }
            ],
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        secret = "example-auth-proxy-secret"
        document = {
            "payload": payload,
            "signature": hmac.new(secret.encode(), canonical, hashlib.sha256).hexdigest(),
        }
        snapshot_path = tmp_path / "snapshot.json"
        snapshot_path.write_text(json.dumps(document), encoding="utf-8")
        config = TeamSyncSourceConfig.create(
            tenant_id="default",
            source_id="auth-proxy-main",
            provider="auth_proxy",
            snapshot_file=str(snapshot_path),
            signature_secret_ref="file:///secret",  # noqa: S106
        )

        snapshot = AuthProxyTeamSyncSource(_SecretResolver(secret)).fetch(config)
        assert snapshot.users[0].subject == "alice"

        document["signature"] = "0" * 64
        snapshot_path.write_text(json.dumps(document), encoding="utf-8")
        with pytest.raises(AccessDeniedError, match="signature is invalid"):
            AuthProxyTeamSyncSource(_SecretResolver(secret)).fetch(config)

        target = tmp_path / "target.json"
        target.write_text(json.dumps(document), encoding="utf-8")
        snapshot_path.unlink()
        snapshot_path.symlink_to(target)
        with pytest.raises(ValidationError, match="missing or unsafe"):
            AuthProxyTeamSyncSource(_SecretResolver(secret)).fetch(config)
