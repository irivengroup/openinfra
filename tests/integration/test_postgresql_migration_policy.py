from __future__ import annotations

from pathlib import Path


def test_dcim_site_dependencies_create_one_postgresql_migration() -> None:
    """DCIM rack lifecycle persistence must be carried by exactly one new migration."""
    migrations = sorted(Path("installers/migrations/postgresql").glob("*.sql"))

    assert migrations
    assert migrations[-1].name == "0033_dcim_site_dependencies_rack_lifecycle.sql"
    assert len([path for path in migrations if path.name.startswith("0032_")]) == 1
    assert len([path for path in migrations if path.name.startswith("0033_")]) == 1
