from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SENSITIVE_ARGUMENT_TOKENS = ("password", "passwd", "pwd", "secret", "token")


def test_application_code_has_no_hardcoded_sensitive_keyword_literals() -> None:
    violations: list[str] = []
    for source in sorted((ROOT / "src/openinfra").rglob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for keyword in node.keywords:
                if keyword.arg is None:
                    continue
                normalized = keyword.arg.casefold()
                if not any(token in normalized for token in SENSITIVE_ARGUMENT_TOKENS):
                    continue
                if isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
                    violations.append(
                        f"{source.relative_to(ROOT)}:{keyword.value.lineno}: {keyword.arg}"
                    )
    assert violations == []
