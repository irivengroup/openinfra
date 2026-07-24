from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from openinfra.quality.migration_packaging import (
    MigrationCatalogArchiveBuilder,
    MigrationCatalogSnapshot,
    MigrationFileRecord,
    MigrationPackagingError,
)

from openinfra.quality.release_packaging import (
    InstallerPackagingValidator,
    IsolatedWheelSmokeValidator,
    ReleaseArtifactContentValidator,
    ReleaseArtifactRecord,
    ReleaseChecksumManifest,
    ReleaseManifestBuilder,
    ReleasePackagingAuditService,
    ReleasePackagingError,
    ReleaseSbomBuilder,
    ReleaseSignatureVerifier,
    ReleaseSigningMaterial,
    ReproducibleDistributionBuilder,
)


class FakeDistributionBuilder(ReproducibleDistributionBuilder):
    def build(
        self,
        project_root: Path,
        work_root: Path,
        output_dir: Path,
        source_date_epoch: int,
    ) -> tuple[list[ReleaseArtifactRecord], dict[str, object]]:
        del project_root, work_root
        output_dir.mkdir(parents=True, exist_ok=True)
        wheel = output_dir / "openinfra-test-py3-none-any.whl"
        sdist = output_dir / "openinfra-test.tar.gz"
        wheel.write_bytes(b"wheel")
        sdist.write_bytes(b"sdist")
        return (
            [
                ReleaseArtifactRecord.from_path(wheel, "wheel"),
                ReleaseArtifactRecord.from_path(sdist, "sdist"),
            ],
            {
                "source_date_epoch": source_date_epoch,
                "comparisons": [
                    {"name": wheel.name, "identical": True},
                    {"name": sdist.name, "identical": True},
                ],
            },
        )


class FakeContentValidator(ReleaseArtifactContentValidator):
    def validate(
        self, project_root: Path, artifacts: list[ReleaseArtifactRecord], output_dir: Path
    ) -> None:
        del project_root, artifacts, output_dir


class FakeInstallerValidator(InstallerPackagingValidator):
    def validate(self, project_root: Path, work_root: Path) -> dict[str, object]:
        del project_root, work_root
        return {
            "dry_runs": [
                {
                    "entrypoint": "install.py",
                    "edition": "test",
                    "scope": "test",
                    "transactional_rollback": True,
                }
            ],
            "rollbacks": [{"entrypoint": "install.py", "restored": "file", "count": 1}],
        }


class FakeSmokeValidator(IsolatedWheelSmokeValidator):
    def validate(self, project_root: Path, wheel_path: Path, work_root: Path) -> dict[str, object]:
        del project_root, work_root
        return {
            "python": "python",
            "pip_check": "passed",
            "smoke": "passed",
            "wheel": wheel_path.name,
        }




class FakeMigrationCatalogBuilder(MigrationCatalogArchiveBuilder):
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def build(
        self, project_root: Path, output_dir: Path, source_date_epoch: int
    ) -> tuple[Path, MigrationCatalogSnapshot]:
        del project_root
        if self.fail:
            raise MigrationPackagingError("synthetic migration catalogue failure")
        output_dir.mkdir(parents=True, exist_ok=True)
        archive = output_dir / "openinfra-test-migrations.zip"
        archive.write_bytes(b"migrations")
        postgresql = MigrationFileRecord(
            "postgresql", "0001", "0001_bootstrap.sql", 1, "0" * 64
        )
        oracle = MigrationFileRecord(
            "oracle", "0001", "0001_bootstrap.sql", 1, "1" * 64
        )
        return archive, MigrationCatalogSnapshot(
            release_version="test",
            source_date_epoch=source_date_epoch,
            postgresql=(postgresql,),
            oracle=(oracle,),
            oracle_manifest_sha256="2" * 64,
        )


class TestReleaseSigningMaterial:
    def test_signs_and_verifies_detached_manifest(self, tmp_path: Path) -> None:
        material = ReleaseSigningMaterial.generate_ephemeral()
        manifest = tmp_path / "manifest.json"
        signature = tmp_path / "manifest.json.sig"
        public_key = tmp_path / "manifest.json.pub"
        manifest.write_bytes(b'{"release":"test"}\n')
        signature.write_bytes(material.sign(manifest.read_bytes()))
        public_key.write_bytes(material.public_key_pem())

        material.verify(manifest.read_bytes(), signature.read_bytes())
        ReleaseSignatureVerifier.verify(public_key, manifest, signature)

        manifest.write_bytes(b'{"release":"tampered"}\n')
        with pytest.raises(ReleasePackagingError, match="signature verification failed"):
            ReleaseSignatureVerifier.verify(public_key, manifest, signature)

    def test_loads_trusted_key_from_file_and_environment(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        private_key = Ed25519PrivateKey.generate()
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        path = tmp_path / "release.pem"
        path.write_bytes(pem)
        monkeypatch.setenv(
            "OPENINFRA_RELEASE_SIGNING_PRIVATE_KEY_B64",
            base64.b64encode(pem).decode("ascii"),
        )

        from_file = ReleaseSigningMaterial.from_file(path)
        from_environment = ReleaseSigningMaterial.from_environment()

        assert from_file.trusted is True
        assert from_file.origin == "file"
        assert from_environment.trusted is True
        assert from_environment.origin == "environment"
        assert from_file.public_key_sha256() == from_environment.public_key_sha256()

    def test_rejects_missing_or_non_ed25519_key(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OPENINFRA_RELEASE_SIGNING_PRIVATE_KEY_B64", raising=False)
        with pytest.raises(ReleasePackagingError, match="missing release signing key"):
            ReleaseSigningMaterial.from_environment()
        invalid = tmp_path / "invalid.pem"
        invalid.write_text("not-a-key", encoding="utf-8")
        with pytest.raises(ReleasePackagingError, match="not a valid unencrypted PEM"):
            ReleaseSigningMaterial.from_file(invalid)


class TestReleaseSbomBuilder:
    def test_generates_deterministic_production_spdx_document(self) -> None:
        first = ReleaseSbomBuilder().build(Path.cwd(), 1_700_000_000)
        second = ReleaseSbomBuilder().build(Path.cwd(), 1_700_000_000)

        assert first == second
        assert first["spdxVersion"] == "SPDX-2.3"
        packages = first["packages"]
        assert isinstance(packages, list)
        names = {str(item["name"]) for item in packages if isinstance(item, dict)}
        assert "openinfra" in names
        assert "cryptography" in names
        assert "react" in names
        assert "pytest" not in names
        assert "eslint" not in names
        spdx_ids = [str(item["SPDXID"]) for item in packages if isinstance(item, dict)]
        assert len(spdx_ids) == len(set(spdx_ids))
        assert str(first["documentNamespace"]).startswith("urn:openinfra:spdx:")


class TestIsolatedWheelSmokeValidator:
    def test_removes_source_tree_overrides_from_environment(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PYTHONPATH", "src")
        monkeypatch.setenv("PYTHONHOME", str(tmp_path / "python-home"))

        environment = IsolatedWheelSmokeValidator._isolated_environment()

        assert "PYTHONPATH" not in environment
        assert "PYTHONHOME" not in environment
        assert environment["PYTHONNOUSERSITE"] == "1"


class TestReleaseChecksumManifest:
    def test_detects_tampered_release_file(self, tmp_path: Path) -> None:
        first = tmp_path / "first.bin"
        second = tmp_path / "second.bin"
        manifest = tmp_path / "SHA256SUMS"
        first.write_bytes(b"first")
        second.write_bytes(b"second")
        ReleaseChecksumManifest.write(manifest, [first, second])
        ReleaseChecksumManifest.verify(manifest, tmp_path)

        second.write_bytes(b"tampered")
        with pytest.raises(ReleasePackagingError, match="checksum mismatch"):
            ReleaseChecksumManifest.verify(manifest, tmp_path)

    def test_rejects_unsafe_manifest_path(self, tmp_path: Path) -> None:
        manifest = tmp_path / "SHA256SUMS"
        manifest.write_text("0" * 64 + "  ../escape.bin\n", encoding="utf-8")

        with pytest.raises(ReleasePackagingError, match="unsafe path"):
            ReleaseChecksumManifest.verify(manifest, tmp_path)


class TestReleaseManifestBuilder:
    def test_records_signing_rollback_and_migrations(self, tmp_path: Path) -> None:
        migrations = tmp_path / "installers/migrations/postgresql"
        migrations.mkdir(parents=True)
        (migrations / "0001.sql").write_text("SELECT 1;", encoding="utf-8")
        artifact_path = tmp_path / "artifact.whl"
        sbom_path = tmp_path / "sbom.json"
        artifact_path.write_bytes(b"wheel")
        sbom_path.write_bytes(b"{}")
        material = ReleaseSigningMaterial.generate_ephemeral()

        manifest = ReleaseManifestBuilder().build(
            1_700_000_000,
            [ReleaseArtifactRecord.from_path(artifact_path, "wheel")],
            ReleaseArtifactRecord.from_path(sbom_path, "spdx-sbom"),
            {"dry_runs": [], "rollbacks": [{"count": 1}]},
            material,
            tmp_path,
        )

        assert manifest["migrations"] == ["0001.sql"]
        assert manifest["rollback"] == {
            "transactional": True,
            "profiles_verified": 1,
            "database_migrations_are_forward_only": True,
            "database_restore_required_if_schema_rollback_is_needed": True,
        }
        signing = manifest["signing"]
        assert isinstance(signing, dict)
        assert signing["algorithm"] == "Ed25519"
        assert signing["trusted"] is False


class TestReleasePackagingAuditService:
    def _service(self) -> ReleasePackagingAuditService:
        return ReleasePackagingAuditService(
            builder=FakeDistributionBuilder(),
            content_validator=FakeContentValidator(),
            installer_validator=FakeInstallerValidator(),
            smoke_validator=FakeSmokeValidator(),
            migration_builder=FakeMigrationCatalogBuilder(),
        )

    def test_ephemeral_key_produces_complete_but_non_certified_report(self, tmp_path: Path) -> None:
        report = self._service().run(
            Path.cwd(),
            tmp_path,
            1_700_000_000,
            ReleaseSigningMaterial.generate_ephemeral(),
        )

        assert report["complete"] is True
        assert report["release_packaging_certification"] is False
        assert report["trusted_signing_key"] is False
        assert "release signing key is ephemeral" in str(report["failures"])
        controls = {item["identifier"] for item in report["controls"]}
        assert "migration-catalog-archive" in controls
        assert (tmp_path / "openinfra-test-migrations.zip").is_file()
        checksum = tmp_path / f"openinfra-{report['release_version']}-SHA256SUMS.txt"
        ReleaseChecksumManifest.verify(checksum, tmp_path)

    def test_trusted_key_certifies_and_writes_verifiable_signature(self, tmp_path: Path) -> None:
        private_key = Ed25519PrivateKey.generate()
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        key_path = tmp_path / "release.pem"
        key_path.write_bytes(pem)
        output = tmp_path / "dist"

        report = self._service().run(
            Path.cwd(),
            output,
            1_700_000_000,
            ReleaseSigningMaterial.from_file(key_path),
        )

        assert report["release_packaging_certification"] is True
        version = str(report["release_version"])
        manifest = output / f"openinfra-{version}-release-manifest.json"
        ReleaseSignatureVerifier.verify(
            manifest.with_suffix(manifest.suffix + ".pub"),
            manifest,
            manifest.with_suffix(manifest.suffix + ".sig"),
        )
        stored = json.loads(
            (output / f"openinfra-{version}-release-packaging-report.json").read_text()
        )
        assert stored == report

    def test_rejects_migration_catalog_failure(self, tmp_path: Path) -> None:
        service = ReleasePackagingAuditService(
            builder=FakeDistributionBuilder(),
            content_validator=FakeContentValidator(),
            installer_validator=FakeInstallerValidator(),
            smoke_validator=FakeSmokeValidator(),
            migration_builder=FakeMigrationCatalogBuilder(fail=True),
        )

        with pytest.raises(ReleasePackagingError, match="synthetic migration catalogue"):
            service.run(
                Path.cwd(),
                tmp_path,
                1_700_000_000,
                ReleaseSigningMaterial.generate_ephemeral(),
            )

    def test_rejects_non_positive_source_epoch(self, tmp_path: Path) -> None:
        with pytest.raises(ReleasePackagingError, match="positive Unix timestamp"):
            self._service().run(
                Path.cwd(),
                tmp_path,
                0,
                ReleaseSigningMaterial.generate_ephemeral(),
            )


class TestReleasePackagingFailureBranches:
    def test_artifact_record_rejects_missing_path(self, tmp_path: Path) -> None:
        with pytest.raises(ReleasePackagingError, match="does not exist"):
            ReleaseArtifactRecord.from_path(tmp_path / "missing.whl", "wheel")

    def test_signing_material_rejects_invalid_base64_missing_file_and_rsa(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cryptography.hazmat.primitives.asymmetric import rsa

        monkeypatch.setenv("OPENINFRA_RELEASE_SIGNING_PRIVATE_KEY_B64", "***")
        with pytest.raises(ReleasePackagingError, match="not valid base64"):
            ReleaseSigningMaterial.from_environment()
        with pytest.raises(ReleasePackagingError, match="does not exist"):
            ReleaseSigningMaterial.from_file(tmp_path / "missing.pem")
        rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        rsa_pem = rsa_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        rsa_path = tmp_path / "rsa.pem"
        rsa_path.write_bytes(rsa_pem)
        with pytest.raises(ReleasePackagingError, match="must use Ed25519"):
            ReleaseSigningMaterial.from_file(rsa_path)

    def test_signature_verifier_rejects_incomplete_invalid_and_rsa_public_key(
        self, tmp_path: Path
    ) -> None:
        from cryptography.hazmat.primitives.asymmetric import rsa

        with pytest.raises(ReleasePackagingError, match="inputs are incomplete"):
            ReleaseSignatureVerifier.verify(
                tmp_path / "missing.pub", tmp_path / "missing.json", tmp_path / "missing.sig"
            )
        payload = tmp_path / "manifest.json"
        signature = tmp_path / "manifest.sig"
        public = tmp_path / "manifest.pub"
        payload.write_bytes(b"{}")
        signature.write_bytes(b"signature")
        public.write_bytes(b"invalid")
        with pytest.raises(ReleasePackagingError, match="not valid PEM"):
            ReleaseSignatureVerifier.verify(public, payload, signature)
        rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public.write_bytes(
            rsa_key.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )
        with pytest.raises(ReleasePackagingError, match="must use Ed25519"):
            ReleaseSignatureVerifier.verify(public, payload, signature)

    def test_sbom_rejects_invalid_dependency_and_lock_shapes(self, tmp_path: Path) -> None:
        builder = ReleaseSbomBuilder()
        with pytest.raises(ReleasePackagingError, match="dependencies must be an array"):
            builder._python_dependencies({"dependencies": "bad"})
        lock = tmp_path / "package-lock.json"
        lock.write_text('{"packages": []}', encoding="utf-8")
        with pytest.raises(ReleasePackagingError, match="packages must be an object"):
            builder._frontend_dependencies(lock)
        with pytest.raises(ReleasePackagingError, match="invalid Python dependency"):
            builder._requirement_name("!!!")
        with pytest.raises(ReleasePackagingError, match="empty package name"):
            builder._spdx_id("npm", "!!!")

    def test_reproducible_builder_success_and_failures(self, tmp_path: Path) -> None:
        class SyntheticBuilder(ReproducibleDistributionBuilder):
            def __init__(self, mode: str) -> None:
                self.mode = mode

            def _run_build(self, project_root: Path, target: Path, source_date_epoch: int) -> None:
                del project_root, source_date_epoch
                target.mkdir(parents=True, exist_ok=True)
                suffix = target.name
                if self.mode == "different-names" and suffix == "build-b":
                    (target / "other.whl").write_bytes(b"wheel")
                    (target / "openinfra.tar.gz").write_bytes(b"sdist")
                    return
                (target / "openinfra.whl").write_bytes(
                    b"different"
                    if self.mode == "different-bytes" and suffix == "build-b"
                    else b"wheel"
                )
                if self.mode != "wheel-only":
                    (target / "openinfra.tar.gz").write_bytes(b"sdist")

        output = tmp_path / "output"
        records, evidence = SyntheticBuilder("ok").build(tmp_path, tmp_path / "work", output, 1)
        assert {item.kind for item in records} == {"wheel", "sdist"}
        assert len(evidence["comparisons"]) == 2
        SyntheticBuilder("ok").build(tmp_path, tmp_path / "work", output, 1)
        with pytest.raises(ReleasePackagingError, match="different artifact names"):
            SyntheticBuilder("different-names").build(
                tmp_path, tmp_path / "names", tmp_path / "names-out", 1
            )
        with pytest.raises(ReleasePackagingError, match="not reproducible"):
            SyntheticBuilder("different-bytes").build(
                tmp_path, tmp_path / "bytes", tmp_path / "bytes-out", 1
            )
        with pytest.raises(ReleasePackagingError, match="exactly one wheel"):
            SyntheticBuilder("wheel-only").build(
                tmp_path, tmp_path / "one", tmp_path / "one-out", 1
            )
        unknown = tmp_path / "unknown.zip"
        unknown.write_bytes(b"zip")
        with pytest.raises(ReleasePackagingError, match="unexpected distribution"):
            ReproducibleDistributionBuilder._artifact_kind(unknown)

    def test_run_build_and_content_validator_subprocess_contracts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import subprocess

        calls: list[dict[str, object]] = []

        def successful_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            del args
            calls.append(kwargs)
            return subprocess.CompletedProcess([], 0, "ok", "")

        monkeypatch.setattr("openinfra.quality.release_packaging.subprocess.run", successful_run)
        target = tmp_path / "dist"
        target.mkdir()
        ReproducibleDistributionBuilder()._run_build(tmp_path, target, 123)
        env = calls[0]["env"]
        assert isinstance(env, dict)
        assert env["SOURCE_DATE_EPOCH"] == "123"
        artifact = tmp_path / "artifact.whl"
        artifact.write_bytes(b"wheel")
        ReleaseArtifactContentValidator().validate(
            tmp_path, [ReleaseArtifactRecord.from_path(artifact, "wheel")], tmp_path
        )

        def failed_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            del args, kwargs
            return subprocess.CompletedProcess([], 1, "", "failure")

        monkeypatch.setattr("openinfra.quality.release_packaging.subprocess.run", failed_run)
        with pytest.raises(ReleasePackagingError, match="distribution build failed"):
            ReproducibleDistributionBuilder()._run_build(tmp_path, target, 123)
        with pytest.raises(ReleasePackagingError, match="content validation failed"):
            ReleaseArtifactContentValidator().validate(
                tmp_path, [ReleaseArtifactRecord.from_path(artifact, "wheel")], tmp_path
            )

    def test_installer_validator_success_and_failure_contracts(self, tmp_path: Path) -> None:
        class SyntheticInstaller(InstallerPackagingValidator):
            def __init__(self, mode: str) -> None:
                self.mode = mode

            def _run_installer(
                self, project_root: Path, relative: str, mode: str, target: Path
            ) -> dict[str, object]:
                del project_root
                if mode == "--dry-run":
                    if self.mode == "no-plan":
                        return {"plan": {}}
                    return {"plan": {"transactional_rollback": True, "edition": "x", "scope": "y"}}
                expected = target / "opt/openinfra/config/openinfra.conf"
                if self.mode != "not-restored":
                    expected.write_text(f"previous:{relative}\n", encoding="utf-8")
                return {"count": 0 if self.mode == "bad-count" else 1}

        evidence = SyntheticInstaller("ok").validate(tmp_path, tmp_path / "ok")
        assert len(evidence["dry_runs"]) == 6
        assert len(evidence["rollbacks"]) == 6
        with pytest.raises(ReleasePackagingError, match="does not advertise rollback"):
            SyntheticInstaller("no-plan").validate(tmp_path, tmp_path / "no-plan")
        with pytest.raises(ReleasePackagingError, match="did not restore"):
            SyntheticInstaller("not-restored").validate(tmp_path, tmp_path / "not-restored")
        with pytest.raises(ReleasePackagingError, match="count is invalid"):
            SyntheticInstaller("bad-count").validate(tmp_path, tmp_path / "bad-count")

    def test_run_installer_rejects_process_and_payload_errors(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import subprocess

        validator = InstallerPackagingValidator()
        responses = iter(
            (
                subprocess.CompletedProcess([], 1, "", "failed"),
                subprocess.CompletedProcess([], 0, "not-json", ""),
                subprocess.CompletedProcess([], 0, "[]", ""),
                subprocess.CompletedProcess([], 0, '{"count": 1}', ""),
            )
        )
        monkeypatch.setattr(
            "openinfra.quality.release_packaging.subprocess.run",
            lambda *args, **kwargs: next(responses),
        )
        with pytest.raises(ReleasePackagingError, match="installer validation failed"):
            validator._run_installer(tmp_path, "install.py", "--dry-run", tmp_path)
        with pytest.raises(ReleasePackagingError, match="invalid JSON"):
            validator._run_installer(tmp_path, "install.py", "--dry-run", tmp_path)
        with pytest.raises(ReleasePackagingError, match="non-object"):
            validator._run_installer(tmp_path, "install.py", "--dry-run", tmp_path)
        assert validator._run_installer(tmp_path, "install.py", "--rollback", tmp_path) == {
            "count": 1
        }

    @pytest.mark.parametrize(
        ("mode", "returncode", "stdout", "stderr", "expected"),
        (
            (
                "success",
                0,
                '{"pip_check":"passed","smoke":"passed","wheel":"openinfra.whl",'
                '"worker_process_isolated":true,"python":"/tmp/python"}',
                "",
                None,
            ),
            ("worker", 2, "", "worker-failed", "worker failed"),
            ("invalid-json", 0, "not-json", "", "invalid JSON"),
            ("non-object", 0, "[]", "", "non-object"),
            (
                "incomplete",
                0,
                '{"pip_check":"passed","smoke":"failed","wheel":"openinfra.whl",'
                '"worker_process_isolated":true}',
                "",
                "evidence is incomplete",
            ),
        ),
    )
    def test_isolated_wheel_smoke_worker_contract(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mode: str,
        returncode: int,
        stdout: str,
        stderr: str,
        expected: str | None,
    ) -> None:
        import subprocess

        project_root = tmp_path / "project"
        scripts = project_root / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "isolated_wheel_smoke.py").write_text("worker", encoding="utf-8")
        wheel = tmp_path / "openinfra.whl"
        wheel.write_bytes(b"wheel")
        work = tmp_path / "work"
        captured: dict[str, object] = {}

        def run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            captured["args"] = args
            captured["kwargs"] = kwargs
            return subprocess.CompletedProcess([], returncode, stdout, stderr)

        monkeypatch.setattr("openinfra.quality.release_packaging.subprocess.run", run)
        validator = IsolatedWheelSmokeValidator()
        if expected is None:
            result = validator.validate(project_root, wheel, work)
            assert result["worker_process_isolated"] is True
            assert "isolated_wheel_smoke.py" in str(captured["args"])
            environment = captured["kwargs"]
            assert isinstance(environment, dict)
            assert environment["env"]["PYTHONNOUSERSITE"] == "1"
        else:
            with pytest.raises(ReleasePackagingError, match=expected):
                validator.validate(project_root, wheel, work)

        windows_root = tmp_path / f"windows-{mode}"
        windows_python = windows_root / "Scripts/python.exe"
        windows_python.parent.mkdir(parents=True)
        windows_python.write_text("", encoding="utf-8")
        assert validator._python_path(windows_root) == windows_python

    def test_isolated_wheel_smoke_worker_timeout_and_missing_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import subprocess

        validator = IsolatedWheelSmokeValidator()
        wheel = tmp_path / "openinfra.whl"
        wheel.write_bytes(b"wheel")
        with pytest.raises(ReleasePackagingError, match="does not exist"):
            validator.validate(tmp_path, wheel, tmp_path / "work")
        worker = tmp_path / "scripts/isolated_wheel_smoke.py"
        worker.parent.mkdir(parents=True)
        worker.write_text("worker", encoding="utf-8")

        def timeout(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            del args, kwargs
            raise subprocess.TimeoutExpired(["worker"], 1)

        monkeypatch.setattr("openinfra.quality.release_packaging.subprocess.run", timeout)
        with pytest.raises(ReleasePackagingError, match="exceeded"):
            validator.validate(tmp_path, wheel, tmp_path / "work")

    def test_checksum_and_manifest_validation_failures(self, tmp_path: Path) -> None:
        missing = tmp_path / "missing-SHA256SUMS"
        with pytest.raises(ReleasePackagingError, match="does not exist"):
            ReleaseChecksumManifest.verify(missing, tmp_path)
        invalid = tmp_path / "invalid-SHA256SUMS"
        invalid.write_text("invalid\n", encoding="utf-8")
        with pytest.raises(ReleasePackagingError, match="invalid line"):
            ReleaseChecksumManifest.verify(invalid, tmp_path)
        absent = tmp_path / "absent-SHA256SUMS"
        absent.write_text("0" * 64 + "  absent.bin\n", encoding="utf-8")
        with pytest.raises(ReleasePackagingError, match="is missing"):
            ReleaseChecksumManifest.verify(absent, tmp_path)
        with pytest.raises(ReleasePackagingError, match="rollback evidence must be an array"):
            ReleaseManifestBuilder().build(
                1,
                [],
                ReleaseArtifactRecord("sbom", "spdx-sbom", 0, "0" * 64),
                {"rollbacks": "invalid"},
                ReleaseSigningMaterial.generate_ephemeral(),
                tmp_path,
            )

    def test_audit_rejects_version_mismatch_and_invalid_sbom_packages(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project = tmp_path / "project"
        project.mkdir()
        (project / "VERSION").write_text("9.9.9\n", encoding="utf-8")
        service = ReleasePackagingAuditService(
            builder=FakeDistributionBuilder(),
            content_validator=FakeContentValidator(),
            installer_validator=FakeInstallerValidator(),
            smoke_validator=FakeSmokeValidator(),
        )
        with pytest.raises(ReleasePackagingError, match="version mismatch"):
            service.run(project, tmp_path / "out", 1, ReleaseSigningMaterial.generate_ephemeral())

        monkeypatch.setattr(
            ReleaseSbomBuilder,
            "build",
            lambda self, project_root, source_date_epoch: {"packages": "invalid"},
        )
        with pytest.raises(ReleasePackagingError, match="SPDX packages must be an array"):
            service.run(
                Path.cwd(), tmp_path / "sbom", 1, ReleaseSigningMaterial.generate_ephemeral()
            )
