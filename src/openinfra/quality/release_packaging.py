from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess  # nosec B404
import sys
import tempfile
import time
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from openinfra import __version__
from openinfra.quality.migration_packaging import (
    MigrationCatalogArchiveBuilder,
    MigrationCatalogSnapshot,
    MigrationPackagingError,
)


class ReleasePackagingError(Exception):
    """Raised when release packaging cannot be validated safely."""


@dataclass(frozen=True, slots=True)
class ReleaseArtifactRecord:
    name: str
    kind: str
    size_bytes: int
    sha256: str

    @classmethod
    def from_path(cls, path: Path, kind: str) -> ReleaseArtifactRecord:
        if not path.is_file():
            raise ReleasePackagingError(f"release artifact does not exist: {path}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return cls(path.name, kind, path.stat().st_size, digest)

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "kind": self.kind,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class ReleasePackagingControlResult:
    identifier: str
    status: str
    duration_ms: float
    detail: str
    evidence: dict[str, object]

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def as_dict(self) -> dict[str, object]:
        return {
            "identifier": self.identifier,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 3),
            "detail": self.detail,
            "evidence": self.evidence,
        }


class ReleaseFileWriter:
    @classmethod
    def write_bytes_atomic(cls, path: Path, payload: bytes, mode: int = 0o644) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
        temporary.write_bytes(payload)
        temporary.chmod(mode)
        temporary.replace(path)

    @classmethod
    def write_json_atomic(cls, path: Path, payload: dict[str, object]) -> None:
        encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        cls.write_bytes_atomic(path, encoded)


class ReleaseSigningMaterial:
    _ENVIRONMENT_VARIABLE: Final[str] = "OPENINFRA_RELEASE_SIGNING_PRIVATE_KEY_B64"

    def __init__(self, private_key: Ed25519PrivateKey, origin: str, trusted: bool) -> None:
        self._private_key = private_key
        self._origin = origin
        self._trusted = trusted

    @property
    def origin(self) -> str:
        return self._origin

    @property
    def trusted(self) -> bool:
        return self._trusted

    @classmethod
    def from_environment(cls) -> ReleaseSigningMaterial:
        encoded = os.environ.get(cls._ENVIRONMENT_VARIABLE, "").strip()
        if not encoded:
            raise ReleasePackagingError(
                f"missing release signing key environment variable: {cls._ENVIRONMENT_VARIABLE}"
            )
        try:
            payload = base64.b64decode(encoded, validate=True)
        except ValueError as exc:
            raise ReleasePackagingError("release signing key is not valid base64") from exc
        return cls(cls._load_private_key(payload), "environment", True)

    @classmethod
    def from_file(cls, path: Path) -> ReleaseSigningMaterial:
        if not path.is_file():
            raise ReleasePackagingError(f"release signing key does not exist: {path}")
        return cls(cls._load_private_key(path.read_bytes()), "file", True)

    @classmethod
    def generate_ephemeral(cls) -> ReleaseSigningMaterial:
        return cls(Ed25519PrivateKey.generate(), "ephemeral", False)

    @classmethod
    def _load_private_key(cls, payload: bytes) -> Ed25519PrivateKey:
        try:
            loaded = serialization.load_pem_private_key(payload, password=None)
        except (TypeError, ValueError) as exc:
            raise ReleasePackagingError(
                "release signing key is not a valid unencrypted PEM"
            ) from exc
        if not isinstance(loaded, Ed25519PrivateKey):
            raise ReleasePackagingError("release signing key must use Ed25519")
        return loaded

    def sign(self, payload: bytes) -> bytes:
        return self._private_key.sign(payload)

    def public_key_pem(self) -> bytes:
        return self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def public_key_sha256(self) -> str:
        return hashlib.sha256(self.public_key_pem()).hexdigest()

    def verify(self, payload: bytes, signature: bytes) -> None:
        public_key = self._private_key.public_key()
        public_key.verify(signature, payload)


class ReleaseSignatureVerifier:
    @classmethod
    def verify(cls, public_key_path: Path, payload_path: Path, signature_path: Path) -> None:
        if (
            not public_key_path.is_file()
            or not payload_path.is_file()
            or not signature_path.is_file()
        ):
            raise ReleasePackagingError("release signature verification inputs are incomplete")
        try:
            loaded = serialization.load_pem_public_key(public_key_path.read_bytes())
        except (TypeError, ValueError) as exc:
            raise ReleasePackagingError("release public key is not valid PEM") from exc
        if not isinstance(loaded, Ed25519PublicKey):
            raise ReleasePackagingError("release public key must use Ed25519")
        try:
            loaded.verify(signature_path.read_bytes(), payload_path.read_bytes())
        except Exception as exc:
            raise ReleasePackagingError("release manifest signature verification failed") from exc


class ReleaseSbomBuilder:
    _SPDX_VERSION: Final[str] = "SPDX-2.3"

    def build(self, project_root: Path, source_date_epoch: int) -> dict[str, object]:
        pyproject = tomllib.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))
        project = pyproject["project"]
        version = str(project["version"])
        python_dependencies = self._python_dependencies(project)
        frontend_dependencies = self._frontend_dependencies(project_root / "web/package-lock.json")
        packages = [self._openinfra_package(project), *python_dependencies, *frontend_dependencies]
        packages.sort(key=lambda item: str(item["SPDXID"]))
        dependency_ids = [
            str(item["SPDXID"])
            for item in packages
            if str(item["SPDXID"]) != "SPDXRef-Package-openinfra"
        ]
        created = (
            datetime.fromtimestamp(source_date_epoch, tz=UTC).isoformat().replace("+00:00", "Z")
        )
        namespace_seed = json.dumps(packages, sort_keys=True, separators=(",", ":")).encode()
        namespace_digest = hashlib.sha256(namespace_seed).hexdigest()
        relationships: list[dict[str, str]] = [
            {
                "spdxElementId": "SPDXRef-DOCUMENT",
                "relationshipType": "DESCRIBES",
                "relatedSpdxElement": "SPDXRef-Package-openinfra",
            }
        ]
        relationships.extend(
            {
                "spdxElementId": "SPDXRef-Package-openinfra",
                "relationshipType": "DEPENDS_ON",
                "relatedSpdxElement": dependency_id,
            }
            for dependency_id in sorted(dependency_ids)
        )
        return {
            "spdxVersion": self._SPDX_VERSION,
            "dataLicense": "CC0-1.0",
            "SPDXID": "SPDXRef-DOCUMENT",
            "name": f"openinfra-{version}-release-sbom",
            "documentNamespace": f"urn:openinfra:spdx:{version}:{namespace_digest}",
            "creationInfo": {
                "created": created,
                "creators": ["Tool: OpenInfraReleaseSbomBuilder-1"],
            },
            "packages": packages,
            "relationships": relationships,
        }

    def _openinfra_package(self, project: dict[str, object]) -> dict[str, object]:
        version = str(project["version"])
        license_value = str(project.get("license", "NOASSERTION"))
        return {
            "name": str(project["name"]),
            "SPDXID": "SPDXRef-Package-openinfra",
            "versionInfo": version,
            "downloadLocation": "NOASSERTION",
            "filesAnalyzed": False,
            "licenseConcluded": license_value,
            "licenseDeclared": license_value,
            "supplier": "Organization: OpenInfra Project",
            "externalRefs": [
                {
                    "referenceCategory": "PACKAGE-MANAGER",
                    "referenceType": "purl",
                    "referenceLocator": f"pkg:pypi/openinfra@{version}",
                }
            ],
        }

    def _python_dependencies(self, project: dict[str, object]) -> list[dict[str, object]]:
        raw_dependencies_value = project.get("dependencies", [])
        if not isinstance(raw_dependencies_value, list):
            raise ReleasePackagingError("project dependencies must be an array")
        raw_dependencies: list[object] = list(raw_dependencies_value)
        optional = project.get("optional-dependencies", {})
        if isinstance(optional, dict):
            for group in ("postgresql", "ldap"):
                values = optional.get(group, [])
                if isinstance(values, list):
                    raw_dependencies.extend(values)
        packages: list[dict[str, object]] = []
        for raw in sorted({str(item) for item in raw_dependencies}):
            name = self._requirement_name(raw)
            packages.append(
                {
                    "name": name,
                    "SPDXID": self._spdx_id("python", name),
                    "versionInfo": raw,
                    "downloadLocation": "NOASSERTION",
                    "filesAnalyzed": False,
                    "licenseConcluded": "NOASSERTION",
                    "licenseDeclared": "NOASSERTION",
                    "externalRefs": [
                        {
                            "referenceCategory": "PACKAGE-MANAGER",
                            "referenceType": "purl",
                            "referenceLocator": f"pkg:pypi/{name.lower()}",
                        }
                    ],
                    "comment": "Python production dependency constraint from pyproject.toml",
                }
            )
        return packages

    def _frontend_dependencies(self, lock_path: Path) -> list[dict[str, object]]:
        payload = json.loads(lock_path.read_text(encoding="utf-8"))
        packages = payload.get("packages", {})
        if not isinstance(packages, dict):
            raise ReleasePackagingError("web/package-lock.json packages must be an object")
        result: list[dict[str, object]] = []
        for path, raw_value in sorted(packages.items()):
            if not path or not isinstance(raw_value, dict) or bool(raw_value.get("dev", False)):
                continue
            name = str(raw_value.get("name") or str(path).rsplit("node_modules/", 1)[-1])
            version = str(raw_value.get("version", "NOASSERTION"))
            item: dict[str, object] = {
                "name": name,
                "SPDXID": self._spdx_id("npm", f"{name}-{version}-{path}"),
                "versionInfo": version,
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "licenseConcluded": str(raw_value.get("license", "NOASSERTION")),
                "licenseDeclared": str(raw_value.get("license", "NOASSERTION")),
                "externalRefs": [
                    {
                        "referenceCategory": "PACKAGE-MANAGER",
                        "referenceType": "purl",
                        "referenceLocator": f"pkg:npm/{name}@{version}",
                    }
                ],
            }
            integrity = str(raw_value.get("integrity", "")).strip()
            if integrity:
                item["comment"] = f"npm integrity: {integrity}"
            result.append(item)
        return result

    @classmethod
    def _requirement_name(cls, raw: str) -> str:
        matched = re.match(r"^[A-Za-z0-9_.-]+", raw.strip())
        if matched is None:
            raise ReleasePackagingError(f"invalid Python dependency constraint: {raw}")
        return matched.group(0)

    @classmethod
    def _spdx_id(cls, ecosystem: str, name: str) -> str:
        normalized = re.sub(r"[^A-Za-z0-9.-]+", "-", name).strip("-")
        if not normalized:
            raise ReleasePackagingError("cannot derive SPDX identifier from empty package name")
        return f"SPDXRef-Package-{ecosystem}-{normalized}"


class ReproducibleDistributionBuilder:
    def build(
        self,
        project_root: Path,
        work_root: Path,
        output_dir: Path,
        source_date_epoch: int,
    ) -> tuple[list[ReleaseArtifactRecord], dict[str, object]]:
        first = work_root / "build-a"
        second = work_root / "build-b"
        for path in (first, second, output_dir):
            if path.exists():
                shutil.rmtree(path)
            path.mkdir(parents=True, exist_ok=True)
        for target in (first, second):
            self._run_build(project_root, target, source_date_epoch)
        first_files = sorted(path for path in first.iterdir() if path.is_file())
        second_files = sorted(path for path in second.iterdir() if path.is_file())
        if [path.name for path in first_files] != [path.name for path in second_files]:
            raise ReleasePackagingError("reproducible build produced different artifact names")
        records: list[ReleaseArtifactRecord] = []
        comparisons: list[dict[str, object]] = []
        for first_path, second_path in zip(first_files, second_files, strict=True):
            first_record = ReleaseArtifactRecord.from_path(
                first_path, self._artifact_kind(first_path)
            )
            second_record = ReleaseArtifactRecord.from_path(
                second_path, self._artifact_kind(second_path)
            )
            if first_record.sha256 != second_record.sha256:
                raise ReleasePackagingError(
                    f"artifact is not reproducible: {first_path.name} "
                    f"({first_record.sha256} != {second_record.sha256})"
                )
            destination = output_dir / first_path.name
            shutil.copy2(first_path, destination)
            records.append(ReleaseArtifactRecord.from_path(destination, first_record.kind))
            comparisons.append(
                {
                    "name": first_path.name,
                    "sha256_build_a": first_record.sha256,
                    "sha256_build_b": second_record.sha256,
                    "identical": True,
                }
            )
        expected = {"wheel", "sdist"}
        observed = {record.kind for record in records}
        if observed != expected:
            raise ReleasePackagingError(
                "reproducible build must produce exactly one wheel and one source distribution"
            )
        return records, {"source_date_epoch": source_date_epoch, "comparisons": comparisons}

    def _run_build(self, project_root: Path, target: Path, source_date_epoch: int) -> None:
        environment = os.environ.copy()
        environment.update(
            {
                "SOURCE_DATE_EPOCH": str(source_date_epoch),
                "PYTHONHASHSEED": "0",
                "TZ": "UTC",
            }
        )
        completed = subprocess.run(  # noqa: S603  # nosec B603
            (
                sys.executable,
                "-m",
                "build",
                "--no-isolation",
                "--wheel",
                "--sdist",
                "--outdir",
                str(target),
            ),
            cwd=project_root,
            check=False,
            capture_output=True,
            text=True,
            env=environment,
            timeout=900,
        )
        if completed.returncode != 0:
            raise ReleasePackagingError(
                "distribution build failed: " + (completed.stderr or completed.stdout).strip()
            )

    @classmethod
    def _artifact_kind(cls, path: Path) -> str:
        if path.suffix == ".whl":
            return "wheel"
        if path.name.endswith(".tar.gz"):
            return "sdist"
        raise ReleasePackagingError(f"unexpected distribution artifact: {path.name}")


class ReleaseArtifactContentValidator:
    def validate(
        self, project_root: Path, artifacts: list[ReleaseArtifactRecord], output_dir: Path
    ) -> None:
        paths = [str(output_dir / item.name) for item in artifacts]
        completed = subprocess.run(  # noqa: S603  # nosec B603
            (sys.executable, "scripts/verify_artifact.py", *paths),
            cwd=project_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if completed.returncode != 0:
            raise ReleasePackagingError(
                "distribution content validation failed: "
                + (completed.stderr or completed.stdout).strip()
            )


class InstallerPackagingValidator:
    _ENTRYPOINTS: Final[tuple[str, ...]] = (
        "installers/setup/lite/install.py",
        "installers/setup/pro/server/install.py",
        "installers/setup/pro/web/install.py",
        "installers/setup/enterprise/server/install.py",
        "installers/setup/enterprise/web/install.py",
        "installers/setup/enterprise/agent/install.py",
    )

    def validate(self, project_root: Path, work_root: Path) -> dict[str, object]:
        dry_runs: list[dict[str, object]] = []
        rollbacks: list[dict[str, object]] = []
        for index, relative in enumerate(self._ENTRYPOINTS):
            target = work_root / f"installer-{index}"
            target.mkdir(parents=True, exist_ok=True)
            dry_payload = self._run_installer(project_root, relative, "--dry-run", target)
            plan = dry_payload.get("plan")
            if not isinstance(plan, dict) or not bool(plan.get("transactional_rollback")):
                raise ReleasePackagingError(f"installer does not advertise rollback: {relative}")
            dry_runs.append(
                {
                    "entrypoint": relative,
                    "edition": plan.get("edition"),
                    "scope": plan.get("scope"),
                    "transactional_rollback": True,
                }
            )
            self._prepare_rollback_fixture(target, relative)
            rollback_payload = self._run_installer(project_root, relative, "--rollback", target)
            expected = target / "opt/openinfra/config/openinfra.conf"
            if expected.read_text(encoding="utf-8") != f"previous:{relative}\n":
                raise ReleasePackagingError(
                    f"installer rollback did not restore previous file: {relative}"
                )
            rollback_count = rollback_payload.get("count", 0)
            if not isinstance(rollback_count, int) or rollback_count != 1:
                raise ReleasePackagingError(
                    f"installer rollback evidence count is invalid: {relative}"
                )
            rollbacks.append(
                {
                    "entrypoint": relative,
                    "restored": str(expected.relative_to(target)),
                    "count": 1,
                }
            )
        return {"dry_runs": dry_runs, "rollbacks": rollbacks}

    def _run_installer(
        self, project_root: Path, relative: str, mode: str, target: Path
    ) -> dict[str, object]:
        completed = subprocess.run(  # noqa: S603  # nosec B603
            (
                sys.executable,
                relative,
                mode,
                "--target-root",
                str(target),
                "--json",
            ),
            cwd=project_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if completed.returncode != 0:
            raise ReleasePackagingError(
                f"installer validation failed for {relative}: "
                + (completed.stderr or completed.stdout).strip()
            )
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise ReleasePackagingError(f"installer returned invalid JSON: {relative}") from exc
        if not isinstance(payload, dict):
            raise ReleasePackagingError(f"installer returned a non-object payload: {relative}")
        return payload

    @classmethod
    def _prepare_rollback_fixture(cls, target: Path, relative: str) -> None:
        config_root = target / "opt/openinfra/config"
        backup_root = config_root / ".openinfra-rollback"
        backup_root.mkdir(parents=True, exist_ok=True)
        (config_root / "openinfra.conf").write_text(f"current:{relative}\n", encoding="utf-8")
        (backup_root / "openinfra.conf.bak").write_text(f"previous:{relative}\n", encoding="utf-8")


class IsolatedWheelSmokeValidator:
    _WORKER_TIMEOUT_SECONDS: Final[int] = 1500

    def validate(self, project_root: Path, wheel_path: Path, work_root: Path) -> dict[str, object]:
        worker = project_root / "scripts/isolated_wheel_smoke.py"
        if not worker.is_file():
            raise ReleasePackagingError(f"isolated wheel smoke worker does not exist: {worker}")
        try:
            completed = subprocess.run(  # noqa: S603  # nosec B603
                (
                    sys.executable,
                    "-I",
                    str(worker),
                    "--project-root",
                    str(project_root),
                    "--wheel",
                    str(wheel_path),
                    "--work-root",
                    str(work_root),
                ),
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
                timeout=self._WORKER_TIMEOUT_SECONDS,
                env=self._isolated_environment(),
            )
        except subprocess.TimeoutExpired as exc:
            raise ReleasePackagingError(
                f"isolated wheel smoke worker exceeded {self._WORKER_TIMEOUT_SECONDS} seconds"
            ) from exc
        except OSError as exc:
            raise ReleasePackagingError(
                f"isolated wheel smoke worker could not start: {exc}"
            ) from exc
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            suffix = f": {detail}" if detail else ""
            raise ReleasePackagingError(f"isolated wheel smoke worker failed{suffix}")
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise ReleasePackagingError(
                "isolated wheel smoke worker returned invalid JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise ReleasePackagingError("isolated wheel smoke worker returned a non-object payload")
        required = {
            "pip_check": "passed",
            "smoke": "passed",
            "wheel": wheel_path.name,
            "worker_process_isolated": True,
        }
        mismatches = [key for key, expected in required.items() if payload.get(key) != expected]
        if mismatches:
            raise ReleasePackagingError(
                "isolated wheel smoke worker evidence is incomplete: "
                + ", ".join(sorted(mismatches))
            )
        return payload

    @classmethod
    def _isolated_environment(cls) -> dict[str, str]:
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        environment.pop("PYTHONHOME", None)
        environment["PYTHONNOUSERSITE"] = "1"
        return environment

    @classmethod
    def _python_path(cls, environment_root: Path) -> Path:
        windows = environment_root / "Scripts/python.exe"
        return windows if windows.is_file() else environment_root / "bin/python"


class ReleaseChecksumManifest:
    @classmethod
    def write(cls, output_path: Path, paths: list[Path]) -> None:
        lines = [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}" for path in paths]
        ReleaseFileWriter.write_bytes_atomic(
            output_path, ("\n".join(sorted(lines)) + "\n").encode()
        )

    @classmethod
    def verify(cls, manifest_path: Path, root: Path) -> None:
        if not manifest_path.is_file():
            raise ReleasePackagingError("SHA256SUMS manifest does not exist")
        for raw_line in manifest_path.read_text(encoding="utf-8").splitlines():
            digest, separator, name = raw_line.partition("  ")
            if separator != "  " or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ReleasePackagingError("SHA256SUMS contains an invalid line")
            relative = Path(name)
            if relative.is_absolute() or ".." in relative.parts:
                raise ReleasePackagingError("SHA256SUMS contains an unsafe path")
            path = root / relative
            if not path.is_file():
                raise ReleasePackagingError(f"checksummed release file is missing: {name}")
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if not hmac.compare_digest(actual, digest):
                raise ReleasePackagingError(f"release checksum mismatch: {name}")


class ReleaseManifestBuilder:
    def build(
        self,
        source_date_epoch: int,
        artifacts: list[ReleaseArtifactRecord],
        sbom_record: ReleaseArtifactRecord,
        installer_evidence: dict[str, object],
        signing_material: ReleaseSigningMaterial,
        project_root: Path,
        migration_catalog: MigrationCatalogSnapshot | None = None,
    ) -> dict[str, object]:
        migration_names = self._migration_names(project_root)
        rollback_items = installer_evidence.get("rollbacks", [])
        if not isinstance(rollback_items, list):
            raise ReleasePackagingError("installer rollback evidence must be an array")
        return {
            "schema_version": 1,
            "release_version": __version__,
            "generated_at": datetime.fromtimestamp(source_date_epoch, tz=UTC)
            .isoformat()
            .replace("+00:00", "Z"),
            "source_date_epoch": source_date_epoch,
            "artifacts": [
                record.as_dict() for record in sorted(artifacts, key=lambda item: item.name)
            ],
            "sbom": sbom_record.as_dict(),
            "signing": {
                "algorithm": "Ed25519",
                "public_key_sha256": signing_material.public_key_sha256(),
                "origin": signing_material.origin,
                "trusted": signing_material.trusted,
            },
            "installers": installer_evidence,
            "rollback": {
                "transactional": True,
                "profiles_verified": len(rollback_items),
                "database_migrations_are_forward_only": True,
                "database_restore_required_if_schema_rollback_is_needed": True,
            },
            "migrations": migration_names,
            "migration_catalog": (
                migration_catalog.as_dict() if migration_catalog is not None else None
            ),
        }

    @classmethod
    def _migration_names(cls, project_root: Path) -> list[str]:
        root = project_root / "installers/migrations/postgresql"
        return [path.name for path in sorted(root.glob("*.sql"))]


class ReleasePackagingAuditService:
    _REQUIRED_CONTROLS: Final[tuple[str, ...]] = (
        "reproducible-distributions",
        "artifact-content",
        "migration-catalog-archive",
        "isolated-wheel-smoke",
        "installer-dry-run-and-rollback",
        "release-sbom",
        "release-manifest-and-signature",
        "checksums",
    )

    def __init__(
        self,
        builder: ReproducibleDistributionBuilder | None = None,
        content_validator: ReleaseArtifactContentValidator | None = None,
        installer_validator: InstallerPackagingValidator | None = None,
        smoke_validator: IsolatedWheelSmokeValidator | None = None,
        migration_builder: MigrationCatalogArchiveBuilder | None = None,
    ) -> None:
        self._builder = builder or ReproducibleDistributionBuilder()
        self._content_validator = content_validator or ReleaseArtifactContentValidator()
        self._installer_validator = installer_validator or InstallerPackagingValidator()
        self._smoke_validator = smoke_validator or IsolatedWheelSmokeValidator()
        self._migration_builder = migration_builder or MigrationCatalogArchiveBuilder()

    def run(
        self,
        project_root: Path,
        output_dir: Path,
        source_date_epoch: int,
        signing_material: ReleaseSigningMaterial,
    ) -> dict[str, object]:
        project_root = project_root.resolve()
        output_dir = output_dir.resolve()
        if source_date_epoch <= 0:
            raise ReleasePackagingError("SOURCE_DATE_EPOCH must be a positive Unix timestamp")
        version = (project_root / "VERSION").read_text(encoding="utf-8").strip()
        if version != __version__:
            raise ReleasePackagingError(
                f"release version mismatch: VERSION={version}, package={__version__}"
            )
        controls: list[ReleasePackagingControlResult] = []
        output_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="openinfra-release-packaging-") as temporary:
            work_root = Path(temporary)
            started = time.perf_counter()
            artifacts, reproducibility = self._builder.build(
                project_root, work_root, output_dir, source_date_epoch
            )
            controls.append(
                self._passed(
                    "reproducible-distributions",
                    started,
                    "wheel and source distribution are byte-for-byte reproducible",
                    reproducibility,
                )
            )

            started = time.perf_counter()
            self._content_validator.validate(project_root, artifacts, output_dir)
            controls.append(
                self._passed(
                    "artifact-content",
                    started,
                    "wheel and source distribution contain all required runtime and release assets",
                    {"artifacts": [item.name for item in artifacts]},
                )
            )

            started = time.perf_counter()
            try:
                migration_archive, migration_catalog = self._migration_builder.build(
                    project_root, output_dir, source_date_epoch
                )
            except MigrationPackagingError as exc:
                raise ReleasePackagingError(str(exc)) from exc
            migration_record = ReleaseArtifactRecord.from_path(
                migration_archive, "migration-catalog"
            )
            artifacts.append(migration_record)
            controls.append(
                self._passed(
                    "migration-catalog-archive",
                    started,
                    "complete PostgreSQL and Oracle migration catalogues are exposed as a standalone archive",
                    {
                        "artifact": migration_record.as_dict(),
                        "count_per_database": migration_catalog.count,
                        "first_version": migration_catalog.first_version,
                        "last_version": migration_catalog.last_version,
                        "parity": True,
                    },
                )
            )

            started = time.perf_counter()
            wheel = next(output_dir / item.name for item in artifacts if item.kind == "wheel")
            smoke_evidence = self._smoke_validator.validate(project_root, wheel, work_root)
            controls.append(
                self._passed(
                    "isolated-wheel-smoke",
                    started,
                    "wheel installs with runtime dependencies and passes installed-package smoke",
                    smoke_evidence,
                )
            )

            started = time.perf_counter()
            installer_evidence = self._installer_validator.validate(project_root, work_root)
            controls.append(
                self._passed(
                    "installer-dry-run-and-rollback",
                    started,
                    "all six installer profiles expose and execute transactional rollback",
                    installer_evidence,
                )
            )

            started = time.perf_counter()
            sbom_payload = ReleaseSbomBuilder().build(project_root, source_date_epoch)
            sbom_path = output_dir / f"openinfra-{version}.spdx.json"
            ReleaseFileWriter.write_json_atomic(sbom_path, sbom_payload)
            sbom_record = ReleaseArtifactRecord.from_path(sbom_path, "spdx-sbom")
            sbom_packages = sbom_payload.get("packages", [])
            if not isinstance(sbom_packages, list):
                raise ReleasePackagingError("SPDX packages must be an array")
            controls.append(
                self._passed(
                    "release-sbom",
                    started,
                    "deterministic SPDX 2.3 release SBOM generated",
                    {
                        "path": sbom_path.name,
                        "sha256": sbom_record.sha256,
                        "packages": len(sbom_packages),
                    },
                )
            )

            started = time.perf_counter()
            manifest_payload = ReleaseManifestBuilder().build(
                source_date_epoch,
                artifacts,
                sbom_record,
                installer_evidence,
                signing_material,
                project_root,
                migration_catalog,
            )
            manifest_path = output_dir / f"openinfra-{version}-release-manifest.json"
            ReleaseFileWriter.write_json_atomic(manifest_path, manifest_payload)
            signature_path = manifest_path.with_suffix(manifest_path.suffix + ".sig")
            public_key_path = manifest_path.with_suffix(manifest_path.suffix + ".pub")
            ReleaseFileWriter.write_bytes_atomic(
                signature_path, signing_material.sign(manifest_path.read_bytes())
            )
            ReleaseFileWriter.write_bytes_atomic(public_key_path, signing_material.public_key_pem())
            ReleaseSignatureVerifier.verify(public_key_path, manifest_path, signature_path)
            controls.append(
                self._passed(
                    "release-manifest-and-signature",
                    started,
                    "release manifest signed and verified with Ed25519",
                    {
                        "manifest": manifest_path.name,
                        "signature": signature_path.name,
                        "public_key": public_key_path.name,
                        "public_key_sha256": signing_material.public_key_sha256(),
                        "trusted_key": signing_material.trusted,
                        "key_origin": signing_material.origin,
                    },
                )
            )

            started = time.perf_counter()
            checksum_path = output_dir / f"openinfra-{version}-SHA256SUMS.txt"
            signed_files = [
                *(output_dir / item.name for item in artifacts),
                sbom_path,
                manifest_path,
                signature_path,
                public_key_path,
            ]
            ReleaseChecksumManifest.write(checksum_path, signed_files)
            ReleaseChecksumManifest.verify(checksum_path, output_dir)
            controls.append(
                self._passed(
                    "checksums",
                    started,
                    "SHA-256 manifest generated and verified",
                    {
                        "path": checksum_path.name,
                        "entries": len(signed_files),
                        "sha256": hashlib.sha256(checksum_path.read_bytes()).hexdigest(),
                    },
                )
            )

        observed = {item.identifier for item in controls}
        missing = [
            identifier for identifier in self._REQUIRED_CONTROLS if identifier not in observed
        ]
        failures = [f"{item.identifier}: {item.status}" for item in controls if not item.passed] + [
            f"missing required control: {identifier}" for identifier in missing
        ]
        if not signing_material.trusted:
            failures.append(
                "release signing key is ephemeral and is not a trusted release identity"
            )
        complete = not missing and len(controls) == len(self._REQUIRED_CONTROLS)
        certified = complete and not failures
        report: dict[str, object] = {
            "schema_version": 1,
            "release_version": version,
            "release_packaging_certification": certified,
            "complete": complete,
            "source_date_epoch": source_date_epoch,
            "signing_key_origin": signing_material.origin,
            "trusted_signing_key": signing_material.trusted,
            "controls": [item.as_dict() for item in controls],
            "failures": failures,
        }
        ReleaseFileWriter.write_json_atomic(
            output_dir / f"openinfra-{version}-release-packaging-report.json", report
        )
        return report

    @classmethod
    def _passed(
        cls,
        identifier: str,
        started: float,
        detail: str,
        evidence: dict[str, object],
    ) -> ReleasePackagingControlResult:
        return ReleasePackagingControlResult(
            identifier=identifier,
            status="passed",
            duration_ms=(time.perf_counter() - started) * 1000,
            detail=detail,
            evidence=evidence,
        )
