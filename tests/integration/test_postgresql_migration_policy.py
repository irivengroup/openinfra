from __future__ import annotations

from pathlib import Path


def test_structural_increments_create_distinct_postgresql_migrations() -> None:
    """Each structural increment must keep exactly one additive PostgreSQL migration."""
    migrations = sorted(Path("installers/migrations/postgresql").glob("*.sql"))

    assert migrations
    assert migrations[-1].name == "0043_network_config_compliance.sql"
    assert len([path for path in migrations if path.name.startswith("0032_")]) == 1
    assert len([path for path in migrations if path.name.startswith("0033_")]) == 1
    assert len([path for path in migrations if path.name.startswith("0034_")]) == 1
    assert len([path for path in migrations if path.name.startswith("0035_")]) == 1
    assert len([path for path in migrations if path.name.startswith("0036_")]) == 1
    assert len([path for path in migrations if path.name.startswith("0037_")]) == 1
    assert len([path for path in migrations if path.name.startswith("0038_")]) == 1
    assert len([path for path in migrations if path.name.startswith("0039_")]) == 1
    assert len([path for path in migrations if path.name.startswith("0040_")]) == 1
    assert len([path for path in migrations if path.name.startswith("0041_")]) == 1
    assert len([path for path in migrations if path.name.startswith("0043_")]) == 1
