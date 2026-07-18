from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest

from openinfra.domain.common import OpenInfraError
from openinfra.interfaces.server_runtime import OpenInfraServerRuntime


class _Cli:
    calls: list[list[str]] = []

    def run(self, args: list[str]) -> int:
        self.calls.append(args)
        return 17


class TestServerRuntimeComplete:
    def test_all_runtime_actions(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(
            "openinfra.interfaces.server_runtime.RuntimeDatabaseBackendResolver.resolve",
            lambda self, explicit_edition=None: "oracle",
        )
        monkeypatch.setattr("openinfra.interfaces.server_runtime.OpenInfraCLI", _Cli)
        runtime = OpenInfraServerRuntime()
        token = tmp_path / "bootstrap-token"

        ensured: list[tuple[Path, int, int]] = []
        monkeypatch.setattr(runtime, "_openinfra_identity", lambda: (1001, 1002))
        monkeypatch.setattr(
            "openinfra.interfaces.server_runtime.RuntimeBootstrapTokenStore",
            lambda path, uid, gid: SimpleNamespace(ensure=lambda: ensured.append((path, uid, gid))),
        )
        assert (
            runtime.run(Namespace(action="ensure-secret", token_file=token, tenant="default")) == 0
        )
        assert ensured == [(token, 1001, 1002)]

        monkeypatch.setattr(
            runtime, "_invoke_api", lambda backend: 19 if backend == "oracle" else 0
        )
        assert runtime.run(Namespace(action="api", token_file=token, tenant="default")) == 19
        assert runtime.run(Namespace(action="migrate", token_file=token, tenant="default")) == 17
        assert _Cli.calls[-1] == ["database", "apply-migrations", "--backend", "oracle"]

        monkeypatch.setattr(
            "openinfra.interfaces.server_runtime.RuntimeAdvancedIdentityConfigResolver.team_sync_sources",
            lambda self: (),
        )
        assert runtime.run(Namespace(action="team-sync", token_file=token, tenant="default")) == 0
        monkeypatch.setattr(
            "openinfra.interfaces.server_runtime.RuntimeAdvancedIdentityConfigResolver.team_sync_sources",
            lambda self: ("ldap-main",),
        )
        assert runtime.run(Namespace(action="team-sync", token_file=token, tenant="tenant-a")) == 17
        assert _Cli.calls[-1][-4:] == ["--tenant", "tenant-a", "--token-file", str(token)]

        with pytest.raises(OpenInfraError, match="unsupported"):
            runtime.run(Namespace(action="invalid", token_file=token, tenant="default"))

    def test_invoke_api_restores_argv_and_identity_errors(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        previous = list(sys.argv)
        captured: list[list[str]] = []

        def api_main() -> int:
            captured.append(list(sys.argv))
            return 23

        monkeypatch.setattr(
            "openinfra.interfaces.server_runtime.OpenInfraApiEntrypoint.main", api_main
        )
        monkeypatch.setenv("OPENINFRA_EDITION", "pro")
        assert OpenInfraServerRuntime._invoke_api("postgresql") == 23
        assert captured[0][-4:] == ["--backend", "postgresql", "--edition", "pro"]
        assert sys.argv == previous

        monkeypatch.setattr(
            "openinfra.interfaces.server_runtime.pwd.getpwnam",
            lambda name: SimpleNamespace(pw_uid=1200),
        )
        monkeypatch.setattr(
            "openinfra.interfaces.server_runtime.grp.getgrnam",
            lambda name: SimpleNamespace(gr_gid=1300),
        )
        assert OpenInfraServerRuntime._openinfra_identity() == (1200, 1300)
        monkeypatch.setattr(
            "openinfra.interfaces.server_runtime.pwd.getpwnam",
            lambda name: (_ for _ in ()).throw(KeyError(name)),
        )
        with pytest.raises(OpenInfraError, match="system account"):
            OpenInfraServerRuntime._openinfra_identity()

    def test_main_reports_openinfra_errors(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["openinfra-server-runtime", "api"])
        monkeypatch.setattr(
            OpenInfraServerRuntime,
            "run",
            lambda self, args: (_ for _ in ()).throw(OpenInfraError("broken")),
        )
        assert OpenInfraServerRuntime.main() == 2
        assert "broken" in capsys.readouterr().err
