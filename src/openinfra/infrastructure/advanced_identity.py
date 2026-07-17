from __future__ import annotations

import hashlib
import hmac
import importlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast
from urllib.parse import parse_qs, urljoin

import httpx

from openinfra.domain.authentication import ExternalDirectoryConfig
from openinfra.domain.common import AccessDeniedError, ValidationError
from openinfra.domain.federated_identity import (
    FederatedIdentity,
    FederatedProvider,
    HttpsOrigin,
    SamlProviderConfig,
    TeamSyncGroup,
    TeamSyncSnapshot,
    TeamSyncSourceConfig,
    TeamSyncUser,
)
from openinfra.infrastructure.external_identity import (
    EnvironmentSecretResolver,
    LdapIpaDirectoryAuthenticator,
    SecretResolver,
)


class SamlAssertionValidator(Protocol):
    def validate(
        self,
        config: SamlProviderConfig,
        request_data: dict[str, object],
    ) -> FederatedIdentity: ...


@dataclass(frozen=True, slots=True)
class StaticSamlAssertionValidator:
    identity: FederatedIdentity

    def validate(
        self,
        config: SamlProviderConfig,
        request_data: dict[str, object],
    ) -> FederatedIdentity:
        del config
        post_data = request_data.get("post_data", {})
        if not isinstance(post_data, dict) or not str(post_data.get("SAMLResponse", "")):
            raise AccessDeniedError("SAMLResponse is required")
        return self.identity


class Python3SamlAssertionValidator:
    def __init__(self, secret_resolver: SecretResolver | None = None) -> None:
        self._secret_resolver = secret_resolver or EnvironmentSecretResolver()

    def validate(
        self,
        config: SamlProviderConfig,
        request_data: dict[str, object],
    ) -> FederatedIdentity:
        auth_class = self._load_auth_class()
        auth = auth_class(request_data, self._settings(config))
        auth.process_response()
        errors = tuple(str(item) for item in auth.get_errors())
        if errors or not bool(auth.is_authenticated()):
            reason = str(auth.get_last_error_reason() or "SAML assertion rejected")
            raise AccessDeniedError(reason)
        attributes = cast(dict[str, list[str]], auth.get_attributes())
        subject = self._first(attributes, config.subject_attribute) or str(auth.get_nameid() or "")
        display_name = self._first(attributes, config.display_name_attribute) or subject
        email = self._first(attributes, config.email_attribute)
        groups = tuple(attributes.get(config.groups_attribute, ()))
        return FederatedIdentity.create(
            provider=FederatedProvider.SAML.value,
            subject=subject,
            display_name=display_name,
            email=email,
            external_groups=groups,
            session_index=str(auth.get_session_index() or "") or None,
        )

    def _settings(self, config: SamlProviderConfig) -> dict[str, object]:
        certificate = self._secret_resolver.resolve(config.idp_x509_cert_ref)
        if "BEGIN CERTIFICATE" not in certificate:
            path = Path(certificate)
            if not path.is_file():
                raise ValidationError(
                    "SAML IdP certificate reference did not resolve to PEM content"
                )
            certificate = path.read_text(encoding="utf-8")
        return {
            "strict": True,
            "debug": False,
            "sp": {
                "entityId": config.sp_entity_id,
                "assertionConsumerService": {
                    "url": config.sp_acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
                "NameIDFormat": config.name_id_format,
            },
            "idp": {
                "entityId": config.idp_entity_id,
                "singleSignOnService": {
                    "url": config.idp_sso_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "x509cert": certificate,
            },
            "security": {
                "wantAssertionsSigned": config.want_assertions_signed,
                "wantMessagesSigned": config.want_messages_signed,
                "wantAssertionsEncrypted": False,
                "wantNameIdEncrypted": False,
                "requestedAuthnContext": False,
                "rejectUnsolicitedResponsesWithInResponseTo": False,
                "allowSingleLabelDomains": False,
            },
        }

    @staticmethod
    def _first(attributes: dict[str, list[str]], name: str) -> str | None:
        values = attributes.get(name, [])
        return str(values[0]).strip() if values and str(values[0]).strip() else None

    @staticmethod
    def _load_auth_class() -> Any:
        try:
            module = importlib.import_module("onelogin.saml2.auth")
        except ModuleNotFoundError as exc:
            raise ValidationError(
                "python3-saml production dependency is required for SAML authentication"
            ) from exc
        return module.OneLogin_Saml2_Auth


class TeamSyncSource(Protocol):
    def fetch(self, config: TeamSyncSourceConfig) -> TeamSyncSnapshot: ...


class TeamSyncPayloadParser:
    def parse(self, config: TeamSyncSourceConfig, payload: object) -> TeamSyncSnapshot:
        if not isinstance(payload, dict):
            raise ValidationError("team sync payload must be a JSON object")
        raw_users = payload.get("users", [])
        raw_groups = payload.get("groups", [])
        if not isinstance(raw_users, list) or not isinstance(raw_groups, list):
            raise ValidationError("team sync users and groups must be arrays")
        users = tuple(self._user(item) for item in raw_users)
        groups = tuple(self._group(config, item) for item in raw_groups)
        return TeamSyncSnapshot.create(
            tenant_id=config.tenant_id.value,
            source_id=config.source_id,
            provider=config.provider.value,
            users=users,
            groups=groups,
        )

    def _user(self, value: object) -> TeamSyncUser:
        if not isinstance(value, dict):
            raise ValidationError("team sync user entries must be objects")
        subject = str(value.get("subject") or value.get("username") or value.get("login") or "")
        display_name = str(value.get("display_name") or value.get("displayName") or subject)
        email = value.get("email")
        return TeamSyncUser.create(
            subject=subject,
            display_name=display_name,
            email=None if email is None else str(email),
            active=bool(value.get("active", True)),
        )

    def _group(self, config: TeamSyncSourceConfig, value: object) -> TeamSyncGroup:
        if not isinstance(value, dict):
            raise ValidationError("team sync group entries must be objects")
        raw_name = str(value.get("name") or value.get("id") or "")
        managed_name = self._managed_group_name(config.source_id, raw_name)
        raw_roles = value.get("roles", [])
        raw_members = value.get("members", [])
        if not isinstance(raw_roles, list) or not isinstance(raw_members, list):
            raise ValidationError("team sync group roles and members must be arrays")
        roles = tuple(str(item) for item in raw_roles) or config.roles_for_external_group(raw_name)
        return TeamSyncGroup.create(
            name=managed_name,
            display_name=str(value.get("display_name") or value.get("displayName") or raw_name),
            roles=roles,
            members=tuple(str(item) for item in raw_members),
        )

    @staticmethod
    def _managed_group_name(source_id: str, external_name: str) -> str:
        normalized = re.sub(r"[^a-z0-9_.:-]+", "-", external_name.strip().lower()).strip("-")
        if not normalized:
            normalized = hashlib.sha256(external_name.encode("utf-8")).hexdigest()[:16]
        digest = hashlib.sha256(external_name.encode("utf-8")).hexdigest()[:10]
        candidate = f"sync-{source_id}-{normalized}"[:53] + "-" + digest
        return candidate[:64]


class OAuthTeamSyncSource:
    def __init__(
        self,
        secret_resolver: SecretResolver | None = None,
        client: httpx.Client | None = None,
        parser: TeamSyncPayloadParser | None = None,
    ) -> None:
        self._secret_resolver = secret_resolver or EnvironmentSecretResolver()
        self._client = client
        self._parser = parser or TeamSyncPayloadParser()

    def fetch(self, config: TeamSyncSourceConfig) -> TeamSyncSnapshot:
        if config.provider not in {FederatedProvider.OAUTH, FederatedProvider.OKTA}:
            raise ValidationError("OAuth source requires oauth or okta provider")
        if config.endpoint is None or config.token_ref is None:
            raise ValidationError("OAuth source configuration is incomplete")
        token = self._secret_resolver.resolve(config.token_ref)
        client = self._client or httpx.Client(
            timeout=config.timeout_seconds,
            follow_redirects=False,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )
        close_client = self._client is None
        try:
            if config.provider is FederatedProvider.OKTA:
                payload = self._fetch_okta(client, config, token)
            else:
                payload = self._fetch_generic(client, config, token)
            return self._parser.parse(config, payload)
        finally:
            if close_client:
                client.close()

    def _fetch_generic(
        self,
        client: httpx.Client,
        config: TeamSyncSourceConfig,
        token: str,
    ) -> dict[str, object]:
        endpoint = cast(str, config.endpoint)
        expected_origin = HttpsOrigin.origin(endpoint)
        users: list[object] = []
        groups: list[object] = []
        next_url: str | None = endpoint
        pages = 0
        while next_url is not None:
            self._assert_same_origin(next_url, expected_origin)
            response = client.get(
                next_url,
                headers={"Authorization": "Bearer " + token, "Accept": "application/json"},
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValidationError("OAuth team sync response must be a JSON object")
            page_users = payload.get("users", [])
            page_groups = payload.get("groups", [])
            if not isinstance(page_users, list) or not isinstance(page_groups, list):
                raise ValidationError("OAuth team sync response arrays are invalid")
            users.extend(page_users)
            groups.extend(page_groups)
            raw_next = payload.get("next")
            next_url = None if raw_next in (None, "") else urljoin(endpoint, str(raw_next))
            pages += 1
            if pages > 1000 or len(users) > 100_000 or len(groups) > 20_000:
                raise ValidationError("OAuth team sync pagination exceeds safety limits")
        return {"users": users, "groups": groups}

    def _fetch_okta(
        self,
        client: httpx.Client,
        config: TeamSyncSourceConfig,
        token: str,
    ) -> dict[str, object]:
        base = cast(str, config.endpoint).rstrip("/")
        expected_origin = HttpsOrigin.origin(base)
        headers = {"Authorization": "SSWS " + token, "Accept": "application/json"}
        raw_users = self._get_okta_pages(
            client,
            base + f"/api/v1/users?limit={config.page_size}",
            headers,
            expected_origin,
        )
        users: list[dict[str, object]] = []
        for item in raw_users:
            if not isinstance(item, dict):
                continue
            profile = item.get("profile", {})
            if not isinstance(profile, dict):
                profile = {}
            login = str(profile.get("login") or item.get("id") or "")
            users.append(
                {
                    "subject": login,
                    "display_name": str(
                        profile.get("displayName")
                        or " ".join(
                            part
                            for part in (
                                str(profile.get("firstName") or "").strip(),
                                str(profile.get("lastName") or "").strip(),
                            )
                            if part
                        )
                        or login
                    ),
                    "email": profile.get("email"),
                    "active": str(item.get("status", "ACTIVE"))
                    not in {"DEPROVISIONED", "SUSPENDED"},
                }
            )
        raw_groups = self._get_okta_pages(
            client,
            base + f"/api/v1/groups?limit={config.page_size}",
            headers,
            expected_origin,
        )
        groups: list[dict[str, object]] = []
        id_to_login: dict[str, str] = {}
        for item in raw_users:
            if not isinstance(item, dict):
                continue
            profile = item.get("profile", {})
            if not isinstance(profile, dict):
                profile = {}
            item_id = str(item.get("id") or "")
            id_to_login[item_id] = str(profile.get("login") or item_id)
        for item in raw_groups:
            if not isinstance(item, dict):
                continue
            group_id = str(item.get("id") or "")
            profile = item.get("profile", {})
            if not isinstance(profile, dict):
                profile = {}
            member_rows = self._get_okta_pages(
                client,
                base + f"/api/v1/groups/{group_id}/users?limit={config.page_size}",
                headers,
                expected_origin,
            )
            members = [
                id_to_login.get(str(row.get("id")), str(row.get("id")))
                for row in member_rows
                if isinstance(row, dict)
            ]
            groups.append(
                {
                    "name": str(profile.get("name") or group_id),
                    "display_name": str(profile.get("name") or group_id),
                    "roles": [],
                    "members": members,
                }
            )
        return {"users": users, "groups": groups}

    def _get_okta_pages(
        self,
        client: httpx.Client,
        url: str,
        headers: dict[str, str],
        expected_origin: str,
    ) -> list[object]:
        values: list[object] = []
        next_url: str | None = url
        pages = 0
        while next_url is not None:
            self._assert_same_origin(next_url, expected_origin)
            response = client.get(next_url, headers=headers)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise ValidationError("Okta response must be a JSON array")
            values.extend(payload)
            next_url = self._okta_next_link(response.headers.get("link", ""))
            pages += 1
            if pages > 1000 or len(values) > 100_000:
                raise ValidationError("Okta pagination exceeds safety limits")
        return values

    @staticmethod
    def _okta_next_link(value: str) -> str | None:
        for item in value.split(","):
            if 'rel="next"' not in item:
                continue
            match = re.search(r"<([^>]+)>", item)
            return match.group(1) if match else None
        return None

    @staticmethod
    def _assert_same_origin(url: str, expected_origin: str) -> None:
        normalized = HttpsOrigin.normalize(url, "team sync pagination URL", allow_path=True)
        if HttpsOrigin.origin(normalized) != expected_origin:
            raise ValidationError("team sync pagination must remain on the configured HTTPS origin")


class AuthProxyTeamSyncSource:
    def __init__(
        self,
        secret_resolver: SecretResolver | None = None,
        parser: TeamSyncPayloadParser | None = None,
    ) -> None:
        self._secret_resolver = secret_resolver or EnvironmentSecretResolver()
        self._parser = parser or TeamSyncPayloadParser()

    def fetch(self, config: TeamSyncSourceConfig) -> TeamSyncSnapshot:
        if config.provider is not FederatedProvider.AUTH_PROXY:
            raise ValidationError("auth proxy source requires auth_proxy provider")
        if config.snapshot_file is None or config.signature_secret_ref is None:
            raise ValidationError("auth proxy source configuration is incomplete")
        path = Path(config.snapshot_file)
        if path.is_symlink() or not path.is_file():
            raise ValidationError("auth proxy snapshot file is missing or unsafe")
        document = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ValidationError("auth proxy snapshot must be a JSON object")
        payload = document.get("payload")
        signature = str(document.get("signature", ""))
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        secret = self._secret_resolver.resolve(config.signature_secret_ref).encode("utf-8")
        expected = hmac.new(secret, canonical, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise AccessDeniedError("auth proxy snapshot signature is invalid")
        return self._parser.parse(config, payload)


class SamlHttpRequestFactory:
    @staticmethod
    def create(
        *,
        host: str,
        path: str,
        query_string: str,
        form_data: dict[str, str],
        forwarded_proto: str = "https",
        remote_addr: str = "",
    ) -> dict[str, object]:
        query = {key: values[-1] for key, values in parse_qs(query_string).items() if values}
        return {
            "https": "on" if forwarded_proto.lower() == "https" else "off",
            "http_host": host,
            "server_port": "443" if forwarded_proto.lower() == "https" else "80",
            "script_name": path,
            "get_data": query,
            "post_data": dict(form_data),
            "remote_addr": remote_addr,
        }


class LdapTeamSyncSource:
    def __init__(
        self,
        directory_config: ExternalDirectoryConfig,
        authenticator: Any | None = None,
        parser: TeamSyncPayloadParser | None = None,
    ) -> None:
        self._directory_config = directory_config
        self._authenticator = authenticator or LdapIpaDirectoryAuthenticator()
        self._parser = parser or TeamSyncPayloadParser()

    def fetch(self, config: TeamSyncSourceConfig) -> TeamSyncSnapshot:
        if config.provider is not FederatedProvider.LDAP:
            raise ValidationError("LDAP team sync source requires ldap provider")
        directory = self._directory_config
        ldap3 = self._authenticator._load_ldap3()
        server = self._authenticator._server(ldap3, directory)
        connection = self._authenticator._service_connection(ldap3, server, directory)
        try:
            user_rows = self._paged_search(
                connection,
                directory.user_base_dn or directory.base_dn,
                directory.user_filter.replace("{username}", "*"),
                (
                    directory.username_attribute,
                    directory.display_name_attribute,
                    directory.email_attribute,
                ),
                directory.page_size,
                directory.size_limit,
            )
            users: list[dict[str, object]] = []
            dn_to_subject: dict[str, str] = {}
            for row in user_rows:
                attrs = self._attributes(row)
                subject = self._first_value(attrs.get(directory.username_attribute))
                if not subject:
                    continue
                dn = str(row.get("dn", "")).strip()
                if dn:
                    dn_to_subject[dn.lower()] = subject
                users.append(
                    {
                        "subject": subject,
                        "display_name": self._first_value(
                            attrs.get(directory.display_name_attribute)
                        )
                        or subject,
                        "email": self._first_value(attrs.get(directory.email_attribute)),
                        "active": True,
                    }
                )
            group_rows = self._paged_search(
                connection,
                directory.group_base_dn or directory.base_dn,
                directory.group_filter.replace("{user_dn}", "*"),
                (directory.group_name_attribute, directory.group_member_attribute),
                directory.page_size,
                directory.size_limit,
            )
            groups: list[dict[str, object]] = []
            for row in group_rows:
                attrs = self._attributes(row)
                name = self._first_value(attrs.get(directory.group_name_attribute))
                if not name:
                    continue
                raw_members = attrs.get(directory.group_member_attribute, [])
                if not isinstance(raw_members, list):
                    raw_members = [raw_members]
                members = [
                    dn_to_subject[str(member).strip().lower()]
                    for member in raw_members
                    if str(member).strip().lower() in dn_to_subject
                ]
                groups.append(
                    {
                        "name": name,
                        "display_name": name,
                        "roles": list(config.roles_for_external_group(name)),
                        "members": members,
                    }
                )
            return self._parser.parse(config, {"users": users, "groups": groups})
        finally:
            self._authenticator._safe_unbind(connection)

    def _paged_search(
        self,
        connection: Any,
        base_dn: str,
        search_filter: str,
        attributes: tuple[str, ...],
        page_size: int,
        size_limit: int,
    ) -> list[dict[str, object]]:
        paged_search = getattr(
            getattr(getattr(connection, "extend", None), "standard", None),
            "paged_search",
            None,
        )
        if callable(paged_search):
            rows = paged_search(
                search_base=base_dn,
                search_filter=search_filter,
                attributes=attributes,
                paged_size=page_size,
                size_limit=size_limit,
                generator=False,
            )
            return [
                cast(dict[str, object], row)
                for row in rows
                if str(row.get("type", "")) == "searchResEntry"
            ]
        connection.search(
            search_base=base_dn,
            search_filter=search_filter,
            attributes=attributes,
            size_limit=size_limit,
        )
        return [
            {
                "dn": str(entry.entry_dn),
                "attributes": cast(dict[str, object], entry.entry_attributes_as_dict),
            }
            for entry in connection.entries
        ]

    @staticmethod
    def _attributes(row: dict[str, object]) -> dict[str, object]:
        value = row.get("attributes", {})
        return cast(dict[str, object], value) if isinstance(value, dict) else {}

    @staticmethod
    def _first_value(value: object) -> str | None:
        if isinstance(value, list):
            value = value[0] if value else None
        normalized = "" if value is None else str(value).strip()
        return normalized or None
