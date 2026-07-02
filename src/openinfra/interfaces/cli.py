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
from openinfra.application.container import ApplicationFactory, OpenInfraApplication
from openinfra.application.dcim_services import LocateEquipmentCommand
from openinfra.application.identity_services import (
    AddUserToGroupCommand,
    CreateGroupCommand,
    CreateUserCommand,
    EffectiveIdentityCommand,
    GrantGroupRoleCommand,
    GrantUserRoleCommand,
)
from openinfra.application.ipam_services import AllocateIpCommand
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
        locate.add_argument("--room", required=True)
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
