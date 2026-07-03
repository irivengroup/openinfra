from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, NoReturn

from openinfra import __version__
from openinfra.application.access_policy_services import (
    CreateAccessPolicyRuleCommand,
    DeactivateAccessPolicyRuleCommand,
    EvaluateAccessPolicyCommand,
    ListAccessPolicyRulesCommand,
)
from openinfra.application.audit_services import (
    ExportAuditEventsCommand,
    ListAuditEventsCommand,
    VerifyAuditIntegrityCommand,
)
from openinfra.application.container import ApplicationFactory, OpenInfraApplication
from openinfra.application.dcim_services import DefinePhysicalRoomCommand, LocateEquipmentCommand
from openinfra.application.identity_services import (
    AddUserToGroupCommand,
    CreateGroupCommand,
    CreateUserCommand,
    EffectiveIdentityCommand,
    GrantGroupRoleCommand,
    GrantUserRoleCommand,
)
from openinfra.application.ipam_services import AllocateIpCommand
from openinfra.application.source_governance_services import (
    CreateSourceGovernanceRuleCommand,
    DeactivateSourceGovernanceRuleCommand,
    EvaluateSourceGovernanceCommand,
    ListSourceGovernanceRulesCommand,
)
from openinfra.application.source_of_truth_services import (
    CreateSourceRelationCommand,
    GetSourceObjectCommand,
    GetSourceObjectVersionCommand,
    ListSourceObjectsCommand,
    ListSourceRelationsCommand,
    UpsertSourceObjectCommand,
)
from openinfra.application.security_services import (
    AuthenticateTokenCommand,
    BootstrapTokenCommand,
    ListTokensCommand,
    RevokeTokenCommand,
    RotateTokenCommand,
)
from openinfra.domain.access_policy import AccessRequestContext
from openinfra.domain.common import OpenInfraError
from openinfra.domain.security import Permission
from openinfra.infrastructure.postgresql import (
    PostgreSQLConnectionFactory,
    PostgreSQLMigrationCatalog,
    PostgreSQLMigrationExecutor,
    PostgreSQLSessionRegistry,
)
from openinfra.infrastructure.spec_validation import ContractualSpecValidator


class OpenInfraCLI:
    @classmethod
    def main(cls) -> int:
        return cls().run(sys.argv[1:])

    def run(self, argv: list[str]) -> int:
        parser = self._build_parser()
        args = parser.parse_args(argv)
        try:
            return int(args.handler(args))
        except OpenInfraError as exc:
            print(f"openinfra: error: {exc}", file=sys.stderr)
            return 2

    def _build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog="openinfra", description="OpenInfra management CLI")
        subparsers = parser.add_subparsers(dest="command", required=True)
        self._add_version_command(subparsers)
        self._add_spec_commands(subparsers)
        self._add_database_commands(subparsers)
        self._add_security_commands(subparsers)
        self._add_identity_commands(subparsers)
        self._add_access_policy_commands(subparsers)
        self._add_audit_commands(subparsers)
        self._add_sot_commands(subparsers)
        self._add_ipam_commands(subparsers)
        self._add_dcim_commands(subparsers)
        return parser

    def _add_version_command(self, subparsers: Any) -> None:
        parser = subparsers.add_parser("version", help="print OpenInfra version")
        parser.set_defaults(handler=self._handle_version)

    def _add_spec_commands(self, subparsers: Any) -> None:
        spec = subparsers.add_parser("spec", help="contractual specification operations")
        spec_subparsers = spec.add_subparsers(dest="spec_command", required=True)
        validate = spec_subparsers.add_parser("validate", help="validate CDC/SFG/STG source files")
        validate.add_argument("--root", type=Path, required=True)
        validate.set_defaults(handler=self._handle_spec_validate)

    def _add_database_commands(self, subparsers: Any) -> None:
        database = subparsers.add_parser("database", help="database operations")
        database_subparsers = database.add_subparsers(dest="database_command", required=True)
        render = database_subparsers.add_parser(
            "render-migration",
            help="render a versioned migration",
        )
        render.add_argument("--name", required=True)
        render.add_argument("--root", type=Path, default=Path("migrations/postgresql"))
        render.set_defaults(handler=self._handle_database_render_migration)
        status = database_subparsers.add_parser(
            "status",
            help="report PostgreSQL schema migration status",
        )
        status.add_argument("--postgres-dsn")
        status.add_argument("--root", type=Path, default=Path("migrations/postgresql"))
        status.set_defaults(handler=self._handle_database_status)
        apply = database_subparsers.add_parser(
            "apply-migrations",
            help="apply PostgreSQL migrations idempotently",
        )
        apply.add_argument("--postgres-dsn")
        apply.add_argument("--root", type=Path, default=Path("migrations/postgresql"))
        apply.add_argument("--dry-run", action="store_true")
        apply.set_defaults(handler=self._handle_database_apply_migrations)

    def _add_security_commands(self, subparsers: Any) -> None:
        security = subparsers.add_parser("security", help="api token and rbac operations")
        security_subparsers = security.add_subparsers(dest="security_command", required=True)
        bootstrap = security_subparsers.add_parser(
            "bootstrap-token",
            help="create or replace an API token hash and role binding",
        )
        bootstrap.add_argument("--backend", choices=("json", "postgresql"), default="json")
        bootstrap.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        bootstrap.add_argument("--postgres-dsn")
        bootstrap.add_argument("--tenant", required=True)
        bootstrap.add_argument("--actor", default="cli")
        bootstrap.add_argument("--subject", required=True)
        bootstrap.add_argument("--role", action="append", default=[])
        bootstrap.add_argument("--token")
        bootstrap.add_argument("--ttl-seconds", type=int)
        bootstrap.set_defaults(handler=self._handle_security_bootstrap_token)
        whoami = security_subparsers.add_parser(
            "whoami",
            help="validate an API token and print the authenticated principal",
        )
        whoami.add_argument("--backend", choices=("json", "postgresql"), default="json")
        whoami.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        whoami.add_argument("--postgres-dsn")
        whoami.add_argument("--tenant", required=True)
        whoami.add_argument("--token", required=True)
        whoami.set_defaults(handler=self._handle_security_whoami)
        revoke = security_subparsers.add_parser(
            "revoke-token",
            help="revoke an API token using a security administrator token",
        )
        revoke.add_argument("--backend", choices=("json", "postgresql"), default="json")
        revoke.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        revoke.add_argument("--postgres-dsn")
        revoke.add_argument("--tenant", required=True)
        revoke.add_argument("--actor", default="cli")
        revoke.add_argument("--target-token", required=True)
        revoke.add_argument("--admin-token")
        revoke.set_defaults(handler=self._handle_security_revoke_token)
        rotate = security_subparsers.add_parser(
            "rotate-token",
            help="rotate a security administrator token and revoke the previous token",
        )
        rotate.add_argument("--backend", choices=("json", "postgresql"), default="json")
        rotate.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        rotate.add_argument("--postgres-dsn")
        rotate.add_argument("--tenant", required=True)
        rotate.add_argument("--actor", default="cli")
        rotate.add_argument("--current-token", required=True)
        rotate.add_argument("--subject")
        rotate.add_argument("--role", action="append", default=[])
        rotate.add_argument("--token")
        rotate.add_argument("--ttl-seconds", type=int)
        rotate.set_defaults(handler=self._handle_security_rotate_token)
        list_tokens = security_subparsers.add_parser(
            "list-tokens",
            help="list API token metadata without exposing token hashes or secrets",
        )
        list_tokens.add_argument("--backend", choices=("json", "postgresql"), default="json")
        list_tokens.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        list_tokens.add_argument("--postgres-dsn")
        list_tokens.add_argument("--tenant", required=True)
        list_tokens.add_argument("--admin-token", required=True)
        list_tokens.add_argument("--limit", type=int, default=100)
        list_tokens.add_argument("--cursor")
        list_tokens.add_argument("--include-inactive", action="store_true")
        list_tokens.set_defaults(handler=self._handle_security_list_tokens)

    def _add_identity_commands(self, subparsers: Any) -> None:
        identity = subparsers.add_parser("identity", help="users, groups and role bindings")
        identity_subparsers = identity.add_subparsers(dest="identity_command", required=True)
        create_user = identity_subparsers.add_parser("create-user", help="upsert an IAM user")
        self._add_backend_arguments(create_user)
        create_user.add_argument("--tenant", required=True)
        create_user.add_argument("--actor", default="cli")
        create_user.add_argument("--admin-token", required=True)
        create_user.add_argument("--username", required=True)
        create_user.add_argument("--display-name", required=True)
        create_user.add_argument("--email")
        create_user.add_argument("--role", action="append", default=[])
        create_user.set_defaults(handler=self._handle_identity_create_user)
        create_group = identity_subparsers.add_parser("create-group", help="upsert an IAM group")
        self._add_backend_arguments(create_group)
        create_group.add_argument("--tenant", required=True)
        create_group.add_argument("--actor", default="cli")
        create_group.add_argument("--admin-token", required=True)
        create_group.add_argument("--name", required=True)
        create_group.add_argument("--display-name", required=True)
        create_group.add_argument("--role", action="append", default=[])
        create_group.set_defaults(handler=self._handle_identity_create_group)
        add_member = identity_subparsers.add_parser(
            "add-user-to-group",
            help="add a user to an IAM group",
        )
        self._add_backend_arguments(add_member)
        add_member.add_argument("--tenant", required=True)
        add_member.add_argument("--actor", default="cli")
        add_member.add_argument("--admin-token", required=True)
        add_member.add_argument("--username", required=True)
        add_member.add_argument("--group", required=True)
        add_member.set_defaults(handler=self._handle_identity_add_user_to_group)
        grant_user = identity_subparsers.add_parser(
            "grant-user-role",
            help="grant a built-in role directly to a user",
        )
        self._add_backend_arguments(grant_user)
        grant_user.add_argument("--tenant", required=True)
        grant_user.add_argument("--actor", default="cli")
        grant_user.add_argument("--admin-token", required=True)
        grant_user.add_argument("--username", required=True)
        grant_user.add_argument("--role", required=True)
        grant_user.set_defaults(handler=self._handle_identity_grant_user_role)
        grant_group = identity_subparsers.add_parser(
            "grant-group-role",
            help="grant a built-in role to a group",
        )
        self._add_backend_arguments(grant_group)
        grant_group.add_argument("--tenant", required=True)
        grant_group.add_argument("--actor", default="cli")
        grant_group.add_argument("--admin-token", required=True)
        grant_group.add_argument("--group", required=True)
        grant_group.add_argument("--role", required=True)
        grant_group.set_defaults(handler=self._handle_identity_grant_group_role)
        effective = identity_subparsers.add_parser(
            "effective",
            help="print effective roles for a user subject",
        )
        self._add_backend_arguments(effective)
        effective.add_argument("--tenant", required=True)
        effective.add_argument("--actor", default="cli")
        effective.add_argument("--admin-token", required=True)
        effective.add_argument("--subject", required=True)
        effective.set_defaults(handler=self._handle_identity_effective)


    def _add_access_policy_commands(self, subparsers: Any) -> None:
        access = subparsers.add_parser("access", help="attribute-based access policy operations")
        access_subparsers = access.add_subparsers(dest="access_command", required=True)
        create_rule = access_subparsers.add_parser("create-rule", help="upsert an ABAC rule")
        self._add_backend_arguments(create_rule)
        create_rule.add_argument("--tenant", required=True)
        create_rule.add_argument("--actor", default="cli")
        create_rule.add_argument("--admin-token", required=True)
        create_rule.add_argument("--name", required=True)
        create_rule.add_argument("--permission", required=True)
        create_rule.add_argument("--effect", choices=("allow", "deny"), required=True)
        create_rule.add_argument("--subject", action="append", default=[])
        create_rule.add_argument("--role", action="append", default=[])
        create_rule.add_argument("--site-code", action="append", default=[])
        create_rule.add_argument("--environment", action="append", default=[])
        create_rule.set_defaults(handler=self._handle_access_create_rule)
        list_rules = access_subparsers.add_parser("list-rules", help="list ABAC rules")
        self._add_backend_arguments(list_rules)
        list_rules.add_argument("--tenant", required=True)
        list_rules.add_argument("--admin-token", required=True)
        list_rules.add_argument("--limit", type=int, default=100)
        list_rules.add_argument("--cursor")
        list_rules.add_argument("--include-inactive", action="store_true")
        list_rules.set_defaults(handler=self._handle_access_list_rules)
        deactivate_rule = access_subparsers.add_parser(
            "deactivate-rule",
            help="deactivate an ABAC rule",
        )
        self._add_backend_arguments(deactivate_rule)
        deactivate_rule.add_argument("--tenant", required=True)
        deactivate_rule.add_argument("--actor", default="cli")
        deactivate_rule.add_argument("--admin-token", required=True)
        deactivate_rule.add_argument("--name", required=True)
        deactivate_rule.set_defaults(handler=self._handle_access_deactivate_rule)
        evaluate = access_subparsers.add_parser("evaluate", help="evaluate token access context")
        self._add_backend_arguments(evaluate)
        evaluate.add_argument("--tenant", required=True)
        evaluate.add_argument("--token", required=True)
        evaluate.add_argument("--permission", required=True)
        evaluate.add_argument("--site-code")
        evaluate.add_argument("--environment")
        evaluate.set_defaults(handler=self._handle_access_evaluate)

    def _add_audit_commands(self, subparsers: Any) -> None:
        audit = subparsers.add_parser("audit", help="audit trail operations")
        audit_subparsers = audit.add_subparsers(dest="audit_command", required=True)
        list_events = audit_subparsers.add_parser("list", help="list audit events safely")
        self._add_backend_arguments(list_events)
        list_events.add_argument("--tenant", required=True)
        list_events.add_argument("--admin-token", required=True)
        list_events.add_argument("--limit", type=int, default=100)
        list_events.add_argument("--cursor")
        list_events.add_argument("--actor")
        list_events.add_argument("--action")
        list_events.add_argument("--target-type")
        list_events.add_argument("--severity")
        list_events.set_defaults(handler=self._handle_audit_list)
        export = audit_subparsers.add_parser("export", help="export audit events as JSON or JSONL")
        self._add_backend_arguments(export)
        export.add_argument("--tenant", required=True)
        export.add_argument("--admin-token", required=True)
        export.add_argument("--format", choices=("json", "jsonl"), default="jsonl")
        export.add_argument("--limit", type=int, default=500)
        export.add_argument("--cursor")
        export.add_argument("--actor")
        export.add_argument("--action")
        export.add_argument("--target-type")
        export.add_argument("--severity")
        export.set_defaults(handler=self._handle_audit_export)
        verify = audit_subparsers.add_parser("verify-integrity", help="verify audit hash chain")
        self._add_backend_arguments(verify)
        verify.add_argument("--tenant", required=True)
        verify.add_argument("--admin-token", required=True)
        verify.add_argument("--limit", type=int, default=500)
        verify.set_defaults(handler=self._handle_audit_verify_integrity)


    def _add_sot_commands(self, subparsers: Any) -> None:
        sot = subparsers.add_parser("sot", help="source of truth objects and relations")
        sot_subparsers = sot.add_subparsers(dest="sot_command", required=True)
        upsert = sot_subparsers.add_parser("upsert-object", help="create or update a SOT object")
        self._add_backend_arguments(upsert)
        upsert.add_argument("--tenant", required=True)
        upsert.add_argument("--actor", default="cli")
        upsert.add_argument("--admin-token", required=True)
        upsert.add_argument("--key", required=True)
        upsert.add_argument(
            "--kind",
            choices=("generic", "device", "interface", "service", "application"),
            required=True,
        )
        upsert.add_argument("--display-name", required=True)
        upsert.add_argument("--attributes-json", default="{}")
        upsert.add_argument("--tag", action="append", default=[])
        upsert.add_argument("--source", required=True)
        upsert.set_defaults(handler=self._handle_sot_upsert_object)
        get_object = sot_subparsers.add_parser("get-object", help="get a SOT object by key")
        self._add_backend_arguments(get_object)
        get_object.add_argument("--tenant", required=True)
        get_object.add_argument("--admin-token", required=True)
        get_object.add_argument("--key", required=True)
        get_object.set_defaults(handler=self._handle_sot_get_object)
        list_objects = sot_subparsers.add_parser("list-objects", help="list SOT objects")
        self._add_backend_arguments(list_objects)
        list_objects.add_argument("--tenant", required=True)
        list_objects.add_argument("--admin-token", required=True)
        list_objects.add_argument("--limit", type=int, default=100)
        list_objects.add_argument("--cursor")
        list_objects.add_argument("--kind")
        list_objects.add_argument("--tag")
        list_objects.set_defaults(handler=self._handle_sot_list_objects)
        get_version = sot_subparsers.add_parser(
            "get-object-version", help="get a SOT object historical version"
        )
        self._add_backend_arguments(get_version)
        get_version.add_argument("--tenant", required=True)
        get_version.add_argument("--admin-token", required=True)
        get_version.add_argument("--key", required=True)
        get_version.add_argument("--version", type=int, required=True)
        get_version.set_defaults(handler=self._handle_sot_get_object_version)
        create_relation = sot_subparsers.add_parser(
            "create-relation", help="create a typed SOT relation"
        )
        self._add_backend_arguments(create_relation)
        create_relation.add_argument("--tenant", required=True)
        create_relation.add_argument("--actor", default="cli")
        create_relation.add_argument("--admin-token", required=True)
        create_relation.add_argument("--relation-type", required=True)
        create_relation.add_argument("--source-key", required=True)
        create_relation.add_argument("--target-key", required=True)
        create_relation.add_argument("--provenance", required=True)
        create_relation.set_defaults(handler=self._handle_sot_create_relation)
        list_relations = sot_subparsers.add_parser(
            "list-relations", help="list typed SOT relations"
        )
        self._add_backend_arguments(list_relations)
        list_relations.add_argument("--tenant", required=True)
        list_relations.add_argument("--admin-token", required=True)
        list_relations.add_argument("--limit", type=int, default=100)
        list_relations.add_argument("--cursor")
        list_relations.add_argument("--source-key")
        list_relations.add_argument("--target-key")
        list_relations.add_argument("--relation-type")
        list_relations.set_defaults(handler=self._handle_sot_list_relations)
        governance_create = sot_subparsers.add_parser(
            "create-governance-rule",
            help="create or update a SOT authoritative source governance rule",
        )
        self._add_backend_arguments(governance_create)
        governance_create.add_argument("--tenant", required=True)
        governance_create.add_argument("--actor", default="cli")
        governance_create.add_argument("--admin-token", required=True)
        governance_create.add_argument("--name", required=True)
        governance_create.add_argument("--object-kind")
        governance_create.add_argument("--attribute-path", required=True)
        governance_create.add_argument("--authoritative-source", required=True)
        governance_create.add_argument("--priority", type=int, default=100)
        governance_create.add_argument("--freshness-seconds", type=int)
        governance_create.add_argument(
            "--conflict-strategy",
            choices=("reject", "accept_with_audit"),
            default="reject",
        )
        governance_create.set_defaults(handler=self._handle_sot_create_governance_rule)
        governance_list = sot_subparsers.add_parser(
            "list-governance-rules",
            help="list SOT governance rules with pagination",
        )
        self._add_backend_arguments(governance_list)
        governance_list.add_argument("--tenant", required=True)
        governance_list.add_argument("--admin-token", required=True)
        governance_list.add_argument("--limit", type=int, default=100)
        governance_list.add_argument("--cursor")
        governance_list.add_argument("--include-inactive", action="store_true")
        governance_list.add_argument("--object-kind")
        governance_list.set_defaults(handler=self._handle_sot_list_governance_rules)
        governance_eval = sot_subparsers.add_parser(
            "evaluate-governance",
            help="evaluate a source update against SOT governance rules",
        )
        self._add_backend_arguments(governance_eval)
        governance_eval.add_argument("--tenant", required=True)
        governance_eval.add_argument("--admin-token", required=True)
        governance_eval.add_argument("--object-kind", required=True)
        governance_eval.add_argument("--incoming-source", required=True)
        governance_eval.add_argument("--existing-attributes-json", default="{}")
        governance_eval.add_argument("--incoming-attributes-json", default="{}")
        governance_eval.set_defaults(handler=self._handle_sot_evaluate_governance)
        governance_deactivate = sot_subparsers.add_parser(
            "deactivate-governance-rule",
            help="deactivate a SOT governance rule",
        )
        self._add_backend_arguments(governance_deactivate)
        governance_deactivate.add_argument("--tenant", required=True)
        governance_deactivate.add_argument("--actor", default="cli")
        governance_deactivate.add_argument("--admin-token", required=True)
        governance_deactivate.add_argument("--name", required=True)
        governance_deactivate.set_defaults(handler=self._handle_sot_deactivate_governance_rule)

    def _add_backend_arguments(self, parser: Any) -> None:
        parser.add_argument("--backend", choices=("json", "postgresql"), default="json")
        parser.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        parser.add_argument("--postgres-dsn")

    def _add_ipam_commands(self, subparsers: Any) -> None:
        ipam = subparsers.add_parser("ipam", help="ipam operations")
        ipam_subparsers = ipam.add_subparsers(dest="ipam_command", required=True)
        allocate = ipam_subparsers.add_parser(
            "allocate",
            help="allocate an address transactionally",
        )
        allocate.add_argument("--backend", choices=("json", "postgresql"), default="json")
        allocate.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        allocate.add_argument("--postgres-dsn")
        allocate.add_argument("--tenant", required=True)
        allocate.add_argument("--actor", default="cli")
        allocate.add_argument("--vrf", required=True)
        allocate.add_argument("--prefix", required=True)
        allocate.add_argument("--hostname", required=True)
        allocate.add_argument("--idempotency-key", required=True)
        allocate.add_argument("--auth-token")
        allocate.add_argument("--site-code")
        allocate.add_argument("--environment")
        allocate.set_defaults(handler=self._handle_ipam_allocate)

    def _add_dcim_commands(self, subparsers: Any) -> None:
        dcim = subparsers.add_parser("dcim", help="dcim operations")
        dcim_subparsers = dcim.add_subparsers(dest="dcim_command", required=True)
        define_room = dcim_subparsers.add_parser(
            "define-room",
            help="define a physical DCIM room hierarchy",
        )
        define_room.add_argument("--backend", choices=("json", "postgresql"), default="json")
        define_room.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        define_room.add_argument("--postgres-dsn")
        define_room.add_argument("--tenant", default="default")
        define_room.add_argument("--actor", default="cli")
        define_room.add_argument("--site-code", required=True)
        define_room.add_argument("--site-name", required=True)
        define_room.add_argument("--country", required=True)
        define_room.add_argument("--region", default="")
        define_room.add_argument("--city", required=True)
        define_room.add_argument("--building-code", required=True)
        define_room.add_argument("--building-name", required=True)
        define_room.add_argument("--floor-code", required=True)
        define_room.add_argument("--floor-name", required=True)
        define_room.add_argument("--floor-index", type=int, required=True)
        define_room.add_argument("--room-code", required=True)
        define_room.add_argument("--room-name", required=True)
        define_room.add_argument("--row", action="append", required=True)
        define_room.add_argument("--column", action="append", required=True)
        define_room.add_argument("--zone-code")
        define_room.add_argument("--zone-name")
        define_room.add_argument("--zone-row", action="append", default=[])
        define_room.add_argument("--zone-column", action="append", default=[])
        define_room.add_argument("--x", type=float)
        define_room.add_argument("--y", type=float)
        define_room.add_argument("--z", type=float)
        define_room.set_defaults(handler=self._handle_dcim_define_room)

        locate = dcim_subparsers.add_parser("locate", help="locate equipment physically")
        locate.add_argument("--backend", choices=("json", "postgresql"), default="json")
        locate.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        locate.add_argument("--postgres-dsn")
        locate.add_argument("--tenant", default="default")
        locate.add_argument("--actor", default="cli")
        locate.add_argument("--asset-tag", required=True)
        locate.add_argument("--equipment-name", default="Unnamed equipment")
        locate.add_argument("--site", required=True)
        locate.add_argument("--building", required=True)
        locate.add_argument("--floor")
        locate.add_argument("--room", required=True)
        locate.add_argument("--zone")
        locate.add_argument("--row", required=True)
        locate.add_argument("--column", required=True)
        locate.add_argument("--rack")
        locate.add_argument("--u-position", type=int)
        locate.add_argument("--x", type=float)
        locate.add_argument("--y", type=float)
        locate.add_argument("--z", type=float)
        locate.set_defaults(handler=self._handle_dcim_locate)

    def _handle_version(self, args: argparse.Namespace) -> int:
        print(__version__)
        return 0

    def _handle_spec_validate(self, args: argparse.Namespace) -> int:
        report = ContractualSpecValidator().assert_valid(args.root)
        print(report.as_text())
        return 0

    def _handle_database_render_migration(self, args: argparse.Namespace) -> int:
        migration = PostgreSQLMigrationCatalog(args.root).load(args.name)
        print(migration.sql, end="")
        return 0

    def _handle_database_status(self, args: argparse.Namespace) -> int:
        executor = self._create_migration_executor(args)
        print(json.dumps(executor.status_as_dict(), sort_keys=True))
        return 0

    def _handle_database_apply_migrations(self, args: argparse.Namespace) -> int:
        executor = self._create_migration_executor(args)
        status = executor.apply_all(dry_run=bool(args.dry_run))
        print(json.dumps(status.as_dict(), sort_keys=True))
        return 0


    def _handle_security_bootstrap_token(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        roles = tuple(args.role) if args.role else ("admin",)
        result = application.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                subject=args.subject,
                roles=roles,
                token=args.token,
                ttl_seconds=args.ttl_seconds,
            )
        )
        print(json.dumps(result.as_dict(), sort_keys=True))
        return 0

    def _handle_security_whoami(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        principal = application.security_service.inspect_token(args.tenant, args.token)
        print(json.dumps(principal.as_dict(), sort_keys=True))
        return 0

    def _handle_security_revoke_token(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.security_service.revoke_token(
            RevokeTokenCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                target_token=args.target_token,
                admin_token=args.admin_token,
            )
        )
        print(json.dumps(result.as_dict(), sort_keys=True))
        return 0

    def _handle_security_rotate_token(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.security_service.rotate_token(
            RotateTokenCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                current_token=args.current_token,
                subject=args.subject,
                roles=tuple(args.role),
                token=args.token,
                ttl_seconds=args.ttl_seconds,
            )
        )
        print(json.dumps(result.as_dict(), sort_keys=True))
        return 0

    def _handle_security_list_tokens(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        page = application.security_service.list_tokens(
            ListTokensCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                limit=args.limit,
                cursor=args.cursor,
                include_inactive=bool(args.include_inactive),
            )
        )
        print(json.dumps(page.as_dict(), sort_keys=True))
        return 0


    def _handle_identity_create_user(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        user = application.identity_service.create_user(
            CreateUserCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                username=args.username,
                display_name=args.display_name,
                email=args.email,
                roles=tuple(args.role),
            )
        )
        print(json.dumps(user.as_dict(), sort_keys=True))
        return 0

    def _handle_identity_create_group(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        group = application.identity_service.create_group(
            CreateGroupCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                name=args.name,
                display_name=args.display_name,
                roles=tuple(args.role),
            )
        )
        print(json.dumps(group.as_dict(), sort_keys=True))
        return 0

    def _handle_identity_add_user_to_group(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        membership = application.identity_service.add_user_to_group(
            AddUserToGroupCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                username=args.username,
                group_name=args.group,
            )
        )
        print(json.dumps(membership.as_dict(), sort_keys=True))
        return 0

    def _handle_identity_grant_user_role(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.identity_service.grant_user_role(
            GrantUserRoleCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                username=args.username,
                role=args.role,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_identity_grant_group_role(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.identity_service.grant_group_role(
            GrantGroupRoleCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                group_name=args.group,
                role=args.role,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_identity_effective(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        identity = application.identity_service.effective_identity(
            EffectiveIdentityCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                subject=args.subject,
            )
        )
        print(json.dumps(identity.as_dict(), sort_keys=True))
        return 0


    def _handle_access_create_rule(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        subjects = tuple(args.subject) if args.subject else ("*",)
        rule = application.access_policy_service.create_rule(
            CreateAccessPolicyRuleCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                name=args.name,
                permission=args.permission,
                effect=args.effect,
                subjects=subjects,
                roles=tuple(args.role),
                site_codes=tuple(args.site_code),
                environments=tuple(args.environment),
            )
        )
        print(json.dumps(rule.as_dict(), sort_keys=True))
        return 0

    def _handle_access_list_rules(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        page = application.access_policy_service.list_rules(
            ListAccessPolicyRulesCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                limit=args.limit,
                cursor=args.cursor,
                include_inactive=bool(args.include_inactive),
            )
        )
        print(json.dumps(page.as_dict(), sort_keys=True))
        return 0

    def _handle_access_deactivate_rule(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.access_policy_service.deactivate_rule(
            DeactivateAccessPolicyRuleCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                name=args.name,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_access_evaluate(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.access_policy_service.evaluate(
            EvaluateAccessPolicyCommand(
                tenant_id=args.tenant,
                token=args.token,
                permission=args.permission,
                site_code=args.site_code,
                environment=args.environment,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_audit_list(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        page = application.audit_service.list_events(
            ListAuditEventsCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                limit=args.limit,
                cursor=args.cursor,
                actor=args.actor,
                action=args.action,
                target_type=args.target_type,
                severity=args.severity,
            )
        )
        print(json.dumps(page.as_dict(), sort_keys=True))
        return 0

    def _handle_audit_export(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        bundle = application.audit_service.export_events(
            ExportAuditEventsCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                format=args.format,
                limit=args.limit,
                cursor=args.cursor,
                actor=args.actor,
                action=args.action,
                target_type=args.target_type,
                severity=args.severity,
            )
        )
        print(json.dumps(bundle.as_dict(), sort_keys=True))
        return 0

    def _handle_audit_verify_integrity(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        report = application.audit_service.verify_integrity(
            VerifyAuditIntegrityCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                limit=args.limit,
            )
        )
        print(json.dumps(report.as_dict(), sort_keys=True))
        return 0


    def _handle_sot_upsert_object(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.source_of_truth_service.upsert_object(
            UpsertSourceObjectCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                key=args.key,
                kind=args.kind,
                display_name=args.display_name,
                attributes_json=args.attributes_json,
                tags=tuple(args.tag),
                source=args.source,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_sot_get_object(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.source_of_truth_service.get_object(
            GetSourceObjectCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                key=args.key,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_sot_list_objects(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        page = application.source_of_truth_service.list_objects(
            ListSourceObjectsCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                limit=args.limit,
                cursor=args.cursor,
                kind=args.kind,
                tag=args.tag,
            )
        )
        print(json.dumps(page.as_dict(), sort_keys=True))
        return 0

    def _handle_sot_get_object_version(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.source_of_truth_service.get_object_version(
            GetSourceObjectVersionCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                key=args.key,
                version=args.version,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_sot_create_relation(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.source_of_truth_service.create_relation(
            CreateSourceRelationCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                relation_type=args.relation_type,
                source_key=args.source_key,
                target_key=args.target_key,
                provenance=args.provenance,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_sot_list_relations(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        page = application.source_of_truth_service.list_relations(
            ListSourceRelationsCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                limit=args.limit,
                cursor=args.cursor,
                source_key=args.source_key,
                target_key=args.target_key,
                relation_type=args.relation_type,
            )
        )
        print(json.dumps(page.as_dict(), sort_keys=True))
        return 0

    def _handle_sot_create_governance_rule(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        rule = application.source_governance_service.create_rule(
            CreateSourceGovernanceRuleCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                name=args.name,
                object_kind=args.object_kind,
                attribute_path=args.attribute_path,
                authoritative_source=args.authoritative_source,
                priority=args.priority,
                freshness_seconds=args.freshness_seconds,
                conflict_strategy=args.conflict_strategy,
            )
        )
        print(json.dumps(rule.as_dict(), sort_keys=True))
        return 0

    def _handle_sot_list_governance_rules(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        page = application.source_governance_service.list_rules(
            ListSourceGovernanceRulesCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                limit=args.limit,
                cursor=args.cursor,
                include_inactive=bool(args.include_inactive),
                object_kind=args.object_kind,
            )
        )
        print(json.dumps(page.as_dict(), sort_keys=True))
        return 0

    def _handle_sot_evaluate_governance(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.source_governance_service.evaluate(
            EvaluateSourceGovernanceCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                object_kind=args.object_kind,
                incoming_source=args.incoming_source,
                existing_attributes_json=args.existing_attributes_json,
                incoming_attributes_json=args.incoming_attributes_json,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_sot_deactivate_governance_rule(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.source_governance_service.deactivate_rule(
            DeactivateSourceGovernanceRuleCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                name=args.name,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_ipam_allocate(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        actor = args.actor
        if args.auth_token:
            principal = application.security_service.authenticate_token(
                AuthenticateTokenCommand(args.tenant, args.auth_token, Permission.IPAM_ALLOCATE)
            )
            application.access_policy_service.authorize(
                principal,
                AccessRequestContext.create(
                    principal.tenant_id,
                    Permission.IPAM_ALLOCATE,
                    args.site_code,
                    args.environment,
                ),
            )
            actor = principal.subject
        result = application.ipam_service.allocate(
            AllocateIpCommand(
                tenant_id=args.tenant,
                actor=actor,
                vrf=args.vrf,
                prefix=args.prefix,
                hostname=args.hostname,
                idempotency_key=args.idempotency_key,
            )
        )
        print(json.dumps(result.as_dict(), sort_keys=True))
        return 0

    def _handle_dcim_define_room(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.define_room(
            DefinePhysicalRoomCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                site_code=args.site_code,
                site_name=args.site_name,
                country=args.country,
                region=args.region,
                city=args.city,
                building_code=args.building_code,
                building_name=args.building_name,
                floor_code=args.floor_code,
                floor_name=args.floor_name,
                floor_index=args.floor_index,
                room_code=args.room_code,
                room_name=args.room_name,
                rows=tuple(args.row),
                columns=tuple(args.column),
                zone_code=args.zone_code,
                zone_name=args.zone_name,
                zone_rows=tuple(args.zone_row),
                zone_columns=tuple(args.zone_column),
                x=args.x,
                y=args.y,
                z=args.z,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_locate(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        equipment = application.dcim_service.locate_equipment(
            LocateEquipmentCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                asset_tag=args.asset_tag,
                equipment_name=args.equipment_name,
                site=args.site,
                building=args.building,
                room=args.room,
                floor=args.floor,
                zone=args.zone,
                row=args.row,
                column=args.column,
                rack=args.rack,
                u_position=args.u_position,
                x=args.x,
                y=args.y,
                z=args.z,
            )
        )
        print(equipment.location.human_readable())
        return 0

    def _create_migration_executor(self, args: argparse.Namespace) -> PostgreSQLMigrationExecutor:
        dsn = args.postgres_dsn or os.environ.get("OPENINFRA_DATABASE_DSN", "")
        if not dsn:
            raise OpenInfraError(
                "--postgres-dsn or OPENINFRA_DATABASE_DSN is required for PostgreSQL migrations"
            )
        registry = PostgreSQLSessionRegistry(PostgreSQLConnectionFactory(dsn))
        return PostgreSQLMigrationExecutor(registry, PostgreSQLMigrationCatalog(args.root))

    def _create_application(self, args: argparse.Namespace) -> OpenInfraApplication:
        backend = str(args.backend)
        if backend == "json":
            return ApplicationFactory().create_json_application(args.data)
        dsn = args.postgres_dsn or os.environ.get("OPENINFRA_DATABASE_DSN", "")
        if not dsn:
            raise OpenInfraError(
                "--postgres-dsn or OPENINFRA_DATABASE_DSN is required for postgresql backend"
            )
        return ApplicationFactory().create_postgresql_application(dsn, seed=False)

    def fail_fast(self, message: str) -> NoReturn:
        raise OpenInfraError(message)


if __name__ == "__main__":
    raise SystemExit(OpenInfraCLI.main())
