from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from openinfra.infrastructure.installer_config import InstallerConfigValidator
from openinfra.infrastructure.runtime_secrets import RuntimeBootstrapTokenStore


class TestAdvancedIdentityServerRuntime:
    def test_systemd_units_use_backend_aware_runtime_and_protected_secrets(self) -> None:
        backend = InstallerConfigValidator().render_systemd_unit("enterprise", "server")
        runtime_secret = Path("installers/systemd/openinfra-runtime-secrets.service").read_text(
            encoding="utf-8"
        )
        migrate = Path("installers/systemd/openinfra-migrate.service").read_text(encoding="utf-8")
        sync_service = Path("installers/systemd/openinfra-team-sync.service").read_text(
            encoding="utf-8"
        )
        sync_timer = Path("installers/systemd/openinfra-team-sync.timer").read_text(
            encoding="utf-8"
        )

        assert "openinfra-server-runtime api" in backend
        assert "Requires=openinfra-migrate.service" in backend
        assert "openinfra-server-runtime ensure-secret" in runtime_secret
        assert "Requires=openinfra-runtime-secrets.service" in migrate
        assert "User=root" in runtime_secret
        assert "openinfra-server-runtime migrate" in migrate
        assert "openinfra-server-runtime team-sync" in sync_service
        assert "Persistent=true" in sync_timer
        assert "ProtectSystem=strict" in backend
        assert "NoNewPrivileges=true" in backend

    @pytest.mark.skipif(os.geteuid() != 0, reason="ownership regression requires root")
    def test_root_created_secret_directory_is_owned_by_runtime_account(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "run" / "openinfra" / "secrets" / "bootstrap-token"
        owner_uid = 10001
        owner_gid = 10001

        store = RuntimeBootstrapTokenStore(path, owner_uid, owner_gid)
        store.ensure()

        assert path.parent.stat().st_uid == owner_uid
        assert path.parent.stat().st_gid == owner_gid
        assert path.stat().st_uid == owner_uid
        assert path.stat().st_gid == owner_gid
        assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
        assert stat.S_IMODE(path.stat().st_mode) == 0o400
