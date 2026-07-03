from __future__ import annotations

import ast
from pathlib import Path


class TestArchitecture:
    def test_product_code_has_no_module_level_functions(self) -> None:
        violations: list[str] = []
        for path in sorted(Path("src/openinfra").rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in tree.body:
                if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                    violations.append(f"{path}:{node.lineno}:{node.name}")

        assert violations == []

    def test_domain_does_not_import_infrastructure_or_interfaces(self) -> None:
        violations: list[str] = []
        for path in sorted(Path("src/openinfra/domain").rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.ImportFrom)
                    and node.module
                    and node.module.startswith(("openinfra.infrastructure", "openinfra.interfaces"))
                ):
                    violations.append(f"{path}:{node.lineno}:{node.module}")

        assert violations == []

    def test_interfaces_do_not_define_business_entities(self) -> None:
        forbidden = {"Site", "Room", "Rack", "Equipment", "Prefix", "IpReservation"}
        violations: list[str] = []
        for path in sorted(Path("src/openinfra/interfaces").rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and node.name in forbidden:
                    violations.append(f"{path}:{node.lineno}:{node.name}")

        assert violations == []
