from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_python_dependency_floors_exclude_current_known_vulnerable_ranges() -> None:
    runtime = (PROJECT_ROOT / "requirements/runtime.txt").read_text(encoding="utf-8")
    development = (PROJECT_ROOT / "requirements/dev.txt").read_text(encoding="utf-8")
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "cryptography>=48.0.1,<50.0" in runtime
    assert '"cryptography>=48.0.1,<50.0"' in pyproject
    assert "urllib3>=2.7.0,<3.0" in development
    assert '"urllib3>=2.7.0,<3.0"' in pyproject
    assert "pip-audit>=2.10.1" in development
    assert '"pip-audit>=2.10.1"' in pyproject


def test_ci_and_container_build_upgrade_to_a_non_vulnerable_pip_floor() -> None:
    workflow = (PROJECT_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert workflow.count('python -m pip install --upgrade "pip>=26.0"') >= 2
    assert 'python -m pip install --upgrade "pip>=26.0"' in dockerfile
    assert "python -m pip_audit --strict --requirement requirements/security-audit.txt" in workflow
