from __future__ import annotations

import sys
import zipfile
from pathlib import Path


class ArtifactVerificationError(Exception):
    """Raised when a packaged artifact does not contain required files."""


class WheelVerifier:
    def verify(self, path: Path) -> None:
        if not path.is_file():
            raise ArtifactVerificationError(f"artifact does not exist: {path}")
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
        required_suffixes = (
            "openinfra/__init__.py",
            "openinfra/domain/dcim.py",
            "openinfra/domain/ipam.py",
            "openinfra/application/dependency_graph_services.py",
            "openinfra/interfaces/cli.py",
            "openinfra/interfaces/rendering/static/assets/openinfra-i18n.js",
            "openinfra/interfaces/rendering/static/assets/openinfra-web.js",
            "openinfra/interfaces/rendering/static/assets/openinfra-web.css",
            "openinfra/api/openapi.yaml",
            "openinfra/migrations/postgresql/0040_dcim_floor_nomenclature.sql",
        )
        missing = [
            suffix
            for suffix in required_suffixes
            if not any(name.endswith(suffix) for name in names)
        ]
        if missing:
            raise ArtifactVerificationError(
                "wheel is missing required files: " + ", ".join(missing)
            )


class ArtifactVerifierCli:
    @classmethod
    def main(cls) -> int:
        if len(sys.argv) < 2:
            print("usage: verify_artifact.py <wheel> [<wheel>...]", file=sys.stderr)
            return 2
        verifier = WheelVerifier()
        try:
            for item in sys.argv[1:]:
                verifier.verify(Path(item))
        except ArtifactVerificationError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0


if __name__ == "__main__":
    raise SystemExit(ArtifactVerifierCli.main())
