from __future__ import annotations

import argparse
import grp
import os
import pwd
import sys
from pathlib import Path

from openinfra.domain.common import OpenInfraError
from openinfra.infrastructure.runtime_config import (
    RuntimeAdvancedIdentityConfigResolver,
    RuntimeDatabaseBackendResolver,
)
from openinfra.infrastructure.runtime_secrets import RuntimeBootstrapTokenStore
from openinfra.interfaces.cli import OpenInfraCLI
from openinfra.interfaces.http_api import OpenInfraApiEntrypoint


class OpenInfraServerRuntime:
    """Native-server bootstrap that resolves trusted runtime configuration internally."""

    @classmethod
    def main(cls) -> int:
        parser = argparse.ArgumentParser(prog="openinfra-server-runtime")
        parser.add_argument("action", choices=("api", "migrate", "ensure-secret", "team-sync"))
        parser.add_argument(
            "--token-file",
            type=Path,
            default=Path("/var/lib/openinfra/secrets/bootstrap-token"),
        )
        parser.add_argument("--tenant", default="default")
        args = parser.parse_args()
        try:
            return cls().run(args)
        except OpenInfraError as exc:
            sys.stderr.write(f"openinfra-server-runtime: error: {exc}\n")
            return 2

    def run(self, args: argparse.Namespace) -> int:
        backend = RuntimeDatabaseBackendResolver().resolve()
        if args.action == "ensure-secret":
            uid, gid = self._openinfra_identity()
            RuntimeBootstrapTokenStore(args.token_file, uid, gid).ensure()
            return 0
        if args.action == "api":
            return self._invoke_api(backend)
        if args.action == "migrate":
            return OpenInfraCLI().run(["database", "apply-migrations", "--backend", backend])
        if args.action == "team-sync":
            sources = RuntimeAdvancedIdentityConfigResolver().team_sync_sources()
            if not sources:
                return 0
            return OpenInfraCLI().run(
                [
                    "identity",
                    "team-sync-runtime",
                    "--backend",
                    backend,
                    "--tenant",
                    args.tenant,
                    "--token-file",
                    str(args.token_file),
                ]
            )
        raise OpenInfraError("unsupported native server runtime action")

    @staticmethod
    def _invoke_api(backend: str) -> int:
        previous = list(sys.argv)
        try:
            sys.argv = [
                "openinfra-api",
                "--backend",
                backend,
                "--edition",
                os.environ.get("OPENINFRA_EDITION", "enterprise"),
            ]
            return OpenInfraApiEntrypoint.main()
        finally:
            sys.argv = previous

    @staticmethod
    def _openinfra_identity() -> tuple[int, int]:
        try:
            account = pwd.getpwnam("openinfra")
            group = grp.getgrnam("openinfra")
        except KeyError as exc:
            raise OpenInfraError("openinfra system account and group are required") from exc
        return int(account.pw_uid), int(group.gr_gid)


if __name__ == "__main__":
    raise SystemExit(OpenInfraServerRuntime.main())
