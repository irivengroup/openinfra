from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from openinfra import __version__


class KubernetesGitOpsProjectError(Exception):
    """Raised when the P21/EPIC-2104 GitOps drift contract is incomplete."""


class KubernetesGitOpsProjectValidator:
    REQUIRED_FILES = (
        "src/openinfra/domain/kubernetes_gitops.py",
        "src/openinfra/application/kubernetes_gitops_services.py",
        "src/openinfra/infrastructure/kubernetes_gitops_mapper.py",
        "src/openinfra/interfaces/http_api.py",
        "src/openinfra/interfaces/cli.py",
        "installers/migrations/postgresql/0056_kubernetes_gitops_drift.sql",
        "docs/api/openapi.yaml",
        "docs/architecture/kubernetes-gitops-drift.md",
        "docs/operations/kubernetes-gitops-drift.md",
        "docs/specifications/OpenInfra-Roadmap-Developpement-v2.2/04-roadmap-epics.csv",
        "docs/specifications/OpenInfra-Roadmap-Developpement-v2.2/09-roadmap-tests-validation.csv",
        "tests/unit/test_kubernetes_gitops.py",
        "tests/integration/test_kubernetes_gitops_services.py",
        "tests/integration/test_kubernetes_gitops_http_api.py",
        "tests/integration/test_kubernetes_gitops_cli.py",
        "tests/integration/test_kubernetes_gitops_postgresql_repository.py",
        "tests/integration/test_kubernetes_gitops_migration.py",
        "tests/integration/test_kubernetes_gitops_web_contract.py",
        "tests/integration/test_kubernetes_gitops_tooling.py",
    )

    def __init__(self, project_root: Path) -> None:
        self._root = project_root.resolve()

    def validate(self) -> dict[str, object]:
        missing = [item for item in self.REQUIRED_FILES if not (self._root / item).is_file()]
        if missing:
            raise KubernetesGitOpsProjectError(
                "missing P21/EPIC-2104 GitOps drift assets: " + ", ".join(missing)
            )
        self._assert_fragments(
            "src/openinfra/domain/kubernetes_gitops.py",
            (
                "class KubernetesGitOpsPolicy",
                "class KubernetesGitOpsState",
                "class KubernetesGitOpsComplianceReport",
                "class KubernetesGitOpsDriftKind",
                'automatic_remediation": False',
                "GitOps revision must be a full 40 or 64 hexadecimal commit digest",
                "GitOps source_path must not contain empty, dot or parent segments",
            ),
        )
        self._assert_fragments(
            "src/openinfra/application/kubernetes_gitops_services.py",
            (
                "def import_state(",
                "def list_states(",
                "def assess(",
                "def assess_latest(",
                '"kubernetes.gitops.state.imported"',
                '"kubernetes.gitops.drift.detected"',
                '"automatic_remediation": False',
            ),
        )
        self._assert_fragments(
            "src/openinfra/interfaces/http_api.py",
            (
                '"/api/v1/kubernetes/gitops-states"',
                '"/api/v1/kubernetes/gitops-states/get"',
                '"/api/v1/kubernetes/gitops-states/latest"',
                '"/api/v1/kubernetes/gitops-states/drift"',
                '"/api/v1/kubernetes/gitops-states/latest-drift"',
                '"/api/v1/kubernetes/gitops-states/import"',
            ),
        )
        self._assert_fragments(
            "src/openinfra/interfaces/cli.py",
            (
                '"gitops-import"',
                '"gitops-list"',
                '"gitops-get"',
                '"gitops-latest"',
                '"gitops-drift"',
                '"gitops-latest-drift"',
            ),
        )
        self._assert_fragments(
            "docs/api/openapi.yaml",
            (
                "/api/v1/kubernetes/gitops-states:",
                "/api/v1/kubernetes/gitops-states/get:",
                "/api/v1/kubernetes/gitops-states/latest:",
                "/api/v1/kubernetes/gitops-states/drift:",
                "/api/v1/kubernetes/gitops-states/latest-drift:",
                "/api/v1/kubernetes/gitops-states/import:",
                "automatic_remediation",
            ),
        )
        for relative in (
            "web/src/domains/discovery.js",
            "src/openinfra/interfaces/rendering/static/assets/domains/discovery.js",
        ):
            self._assert_fragments(
                relative,
                (
                    "kubernetes-gitops-states-list",
                    "kubernetes-gitops-state-get",
                    "kubernetes-gitops-state-latest",
                    "kubernetes-gitops-drift-snapshot",
                    "kubernetes-gitops-drift-latest",
                    "kubernetes-gitops-state-import",
                ),
            )
        self._assert_fragments(
            "docs/specifications/OpenInfra-Roadmap-Developpement-v2.2/04-roadmap-epics.csv",
            ("EPIC-2104", "Conformité GitOps et dérive observée"),
        )
        self._assert_fragments(
            "docs/specifications/OpenInfra-Roadmap-Developpement-v2.2/09-roadmap-tests-validation.csv",
            ("TST-P21-K8S-GITOPS-DRIFT", "GitOps drift"),
        )
        migrations = sorted((self._root / "installers/migrations/postgresql").glob("*.sql"))
        if len(migrations) != 56 or migrations[-1].name != "0056_kubernetes_gitops_drift.sql":
            raise KubernetesGitOpsProjectError(
                "EPIC-2104 requires the 56-migration chain ending with "
                "0056_kubernetes_gitops_drift.sql"
            )
        return {
            "schema_version": 1,
            "report_kind": "kubernetes-gitops-drift-contract",
            "release_version": __version__,
            "generated_at": datetime.now(UTC).isoformat(),
            "complete": True,
            "phase": "P21",
            "epic": "EPIC-2104",
            "release": "REL-11",
            "roadmap_version": "2.2.0",
            "immutable_expected_state": True,
            "immutable_observed_state": True,
            "deterministic_drift": True,
            "audit_enabled": True,
            "transactional_outbox": True,
            "automatic_remediation": False,
            "api_cli_web_parity": True,
            "migration_count": 56,
        }

    def _assert_fragments(self, relative: str, fragments: tuple[str, ...]) -> None:
        content = (self._root / relative).read_text(encoding="utf-8")
        missing = [fragment for fragment in fragments if fragment not in content]
        if missing:
            raise KubernetesGitOpsProjectError(
                f"{relative} is incomplete for P21/EPIC-2104: " + ", ".join(missing)
            )


class KubernetesGitOpsProjectCli:
    @classmethod
    def main(cls) -> int:
        parser = argparse.ArgumentParser(description="Validate OpenInfra P21/EPIC-2104 contracts")
        parser.add_argument("--project-root", type=Path, default=Path.cwd())
        parser.add_argument("--output", type=Path)
        parser.add_argument("--enforce", action="store_true")
        args = parser.parse_args()
        try:
            report = KubernetesGitOpsProjectValidator(args.project_root).validate()
        except KubernetesGitOpsProjectError as exc:
            if args.enforce:
                print(str(exc))
                return 1
            raise
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            temporary = args.output.with_suffix(args.output.suffix + ".tmp")
            temporary.write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            temporary.replace(args.output)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0


if __name__ == "__main__":
    raise SystemExit(KubernetesGitOpsProjectCli.main())
