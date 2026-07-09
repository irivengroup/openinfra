from __future__ import annotations

from pathlib import Path


def test_itam_organization_form_realignment_does_not_create_new_sql_migration() -> None:
    """UI-only ITAM form corrections must not increase PostgreSQL migration count."""
    migrations = sorted(Path("installers/migrations/postgresql").glob("*.sql"))

    assert migrations
    assert migrations[-1].name == "0031_itam_organization_identity.sql"
    assert not any(path.name.startswith("0032_") for path in migrations)
