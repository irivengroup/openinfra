from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from openinfra.infrastructure.installer_config import (
    InstallerConfigValidator,
    InstallerScopeCatalog,
)


@dataclass(frozen=True, slots=True)
class EnterpriseAlignmentReport:
    cdc_root: Path
    roadmap_root: Path
    project_root: Path
    errors: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "cdc_root": str(self.cdc_root),
            "roadmap_root": str(self.roadmap_root),
            "project_root": str(self.project_root),
            "errors": list(self.errors),
        }


class EnterpriseAlignmentValidator:
    _required_cdc_decisions = (
        "CDC-ED-001",
        "CDC-SVC-001",
        "CDC-SVC-002",
        "CDC-SVC-003",
        "CDC-INST-001",
        "CDC-INST-002",
        "CDC-STO-002",
        "CDC-STO-003",
        "CDC-STO-004",
        "CDC-STO-005",
        "CDC-ITSM-001",
        "CDC-PERF-001",
        "CDC-PERF-002",
        "CDC-PERF-003",
    )
    _required_roadmap_phases = tuple(f"P{number:02d}" for number in range(26))
    _required_services = ("openinfra.service", "openinfra-web.service", "openinfra-agent.service")

    def validate(
        self, cdc_root: Path, roadmap_root: Path, project_root: Path
    ) -> EnterpriseAlignmentReport:
        errors: list[str] = []
        self._validate_roots(cdc_root, roadmap_root, errors)
        self._validate_roadmap(roadmap_root, errors)
        self._validate_services(project_root, errors)
        self._validate_installer_plan(roadmap_root, project_root, errors)
        self._validate_installer_configs(project_root, errors)
        return EnterpriseAlignmentReport(cdc_root, roadmap_root, project_root, tuple(errors))

    def _validate_roots(self, cdc_root: Path, roadmap_root: Path, errors: list[str]) -> None:
        for path in (cdc_root / "00-README.md", cdc_root / "00-Delta-v4.11.md"):
            if not path.is_file():
                errors.append(f"missing CDC v4.12.0 file: {path}")
        version_file = roadmap_root / "VERSION"
        if not version_file.is_file():
            errors.append("missing roadmap v2.5 VERSION")
        elif version_file.read_text(encoding="utf-8").strip() != "2.5.0":
            errors.append("roadmap VERSION must be 2.5.0")
        alignment = roadmap_root / "14-alignement-cdc-v4.12.0.csv"
        if not alignment.is_file():
            errors.append("missing CDC v4.12.0 alignment matrix")
            return
        rows = self._read_csv(alignment)
        decision_ids = {row.get("cdc_decision_id", "") for row in rows}
        for decision in self._required_cdc_decisions:
            if decision not in decision_ids:
                errors.append(f"missing CDC decision in roadmap alignment: {decision}")

    def _validate_roadmap(self, roadmap_root: Path, errors: list[str]) -> None:
        phases_file = roadmap_root / "02-roadmap-phases.csv"
        epics_file = roadmap_root / "04-roadmap-epics.csv"
        if not phases_file.is_file() or not epics_file.is_file():
            errors.append("roadmap phases and epics files are required")
            return
        phase_ids = {row.get("id", "") for row in self._read_csv(phases_file)}
        for phase in self._required_roadmap_phases:
            if phase not in phase_ids:
                errors.append(f"missing roadmap phase: {phase}")
        epic_ids = {row.get("id", "") for row in self._read_csv(epics_file)}
        for epic in ("EPIC-0001", "EPIC-0301", "EPIC-0302", "EPIC-0503"):
            if epic not in epic_ids:
                errors.append(f"missing roadmap epic: {epic}")

    def _validate_services(self, project_root: Path, errors: list[str]) -> None:
        if (project_root / "deploy").exists():
            errors.append("deploy directory must be removed; installer renders systemd units")
        validator = InstallerConfigValidator()
        rendered_units = {
            "openinfra.service": validator.render_systemd_unit("enterprise", "server"),
            "openinfra-web.service": validator.render_systemd_unit("enterprise", "web"),
            "openinfra-agent.service": validator.render_systemd_unit("enterprise", "agent"),
        }
        for service in self._required_services:
            unit = rendered_units.get(service, "")
            if service not in unit:
                errors.append(f"installer-rendered unit missing service marker: {service}")
            if "NoNewPrivileges=true" not in unit or "ProtectSystem=strict" not in unit:
                errors.append(f"installer-rendered unit is not hardened: {service}")
        if (
            "ExecStart=/opt/openinfra/venv/bin/openinfra-server-runtime api"
            not in rendered_units["openinfra.service"]
        ):
            errors.append("openinfra.service renderer must launch the backend-aware server runtime")
        enterprise_server = InstallerConfigValidator().validate_file(
            project_root / "installers/setup/enterprise/server/install.ini",
            edition="enterprise",
            scope="server",
        )
        if enterprise_server.postgresql_ha_plan is None:
            errors.append("enterprise server must render a PostgreSQL HA/PITR plan")
        elif not enterprise_server.postgresql_ha_plan.replication_enabled:
            errors.append("enterprise server peer_nodes must enable near-real-time replication")
        if "openinfra database apply-migrations" in rendered_units["openinfra.service"]:
            errors.append("systemd unit must not own database migration execution")
        catalog = InstallerScopeCatalog()
        if len(catalog.policies()) != 6:
            errors.append("installer catalog must expose six edition/scope policies")
        agent_policy = catalog.policy_for("enterprise", "agent")
        if agent_policy is None or not agent_policy.managed_application_filesystem:
            errors.append("enterprise agent must manage application filesystem per CDC")
        for edition, scope in (
            ("lite", "all-in-one"),
            ("pro", "server"),
            ("pro", "web"),
            ("enterprise", "server"),
            ("enterprise", "web"),
            ("enterprise", "agent"),
        ):
            policy = catalog.policy_for(edition, scope)
            if policy is None or not policy.managed_application_filesystem:
                errors.append(f"{edition}/{scope} must manage application filesystem internally")

    def _validate_installer_plan(
        self, roadmap_root: Path, project_root: Path, errors: list[str]
    ) -> None:
        plan = roadmap_root / "16-plan-installateurs.csv"
        if not plan.is_file():
            errors.append("missing installer plan: 16-plan-installateurs.csv")
            return
        rows = self._read_csv(plan)
        for row in rows:
            scope_root = project_root / row["path"]
            config_path = scope_root / "install.ini"
            program_path = scope_root / "install.py"
            if not config_path.is_file():
                errors.append(f"installer plan path missing install.ini: {row['path']}")
            if not program_path.is_file():
                errors.append(f"installer plan path missing install.py: {row['path']}")

    def _validate_installer_configs(self, project_root: Path, errors: list[str]) -> None:
        report = InstallerConfigValidator().validate_tree(project_root / "installers")
        if not report.valid:
            payload = json.dumps(report.as_dict(), sort_keys=True)
            errors.append("installer install.ini validation failed: " + payload)

    def _read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))


class EnterpriseAlignmentCli:
    @classmethod
    def main(cls) -> int:
        parser = argparse.ArgumentParser(
            prog="validate_enterprise_alignment",
            description="Validate OpenInfra project alignment with CDC v4.12.0 and roadmap v2.5.",
        )
        parser.add_argument(
            "--cdc-root",
            type=Path,
            default=Path("docs/specifications/OpenInfra-CDC-SFG-STG-v4.12.0"),
        )
        parser.add_argument(
            "--roadmap-root",
            type=Path,
            default=Path("docs/specifications/OpenInfra-Roadmap-Developpement-v2.5"),
        )
        parser.add_argument("--project-root", type=Path, default=Path("."))
        parser.add_argument("--json", action="store_true")
        args = parser.parse_args()
        report = EnterpriseAlignmentValidator().validate(
            args.cdc_root, args.roadmap_root, args.project_root
        )
        if args.json:
            print(json.dumps(report.as_dict(), sort_keys=True, indent=2))
        else:
            print("status=" + ("PASS" if report.valid else "FAIL"))
            for error in report.errors:
                print("error=" + error)
        return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(EnterpriseAlignmentCli.main())
