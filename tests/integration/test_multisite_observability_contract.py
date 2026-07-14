from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.validate_multisite_observability import (
    MultisiteObservabilityValidationError,
    MultisiteTargetFileValidator,
    validate_project,
)

ROOT = Path(__file__).resolve().parents[2]


def test_multisite_observability_project_contract_is_complete() -> None:
    assert validate_project(ROOT) == {
        "profile_id": "openinfra-multisite-observability-v1",
        "profile_version": 1,
        "required_signals": 6,
        "alerts": 6,
        "status": "passed",
    }


def test_multisite_target_file_validator_accepts_bounded_https_scrape_targets(
    tmp_path: Path,
) -> None:
    target_file = tmp_path / "sites.json"
    target_file.write_text(
        json.dumps(
            [
                {
                    "targets": ["par1.openinfra.internal:443", "par2.openinfra.internal:443"],
                    "labels": {
                        "region": "EU-WEST",
                        "site": "PAR1",
                        "service": "openinfra-api",
                    },
                }
            ]
        ),
        encoding="utf-8",
    )

    assert MultisiteTargetFileValidator.validate_file(target_file) == 2


@pytest.mark.parametrize(
    "payload, message",
    [
        ([], "non-empty array"),
        (
            [
                {
                    "targets": ["https://par1.example.invalid/metrics"],
                    "labels": {
                        "region": "EU-WEST",
                        "site": "PAR1",
                        "service": "openinfra-api",
                    },
                }
            ],
            "invalid host:port",
        ),
        (
            [
                {
                    "targets": ["par1.example.invalid:443"],
                    "labels": {
                        "region": "EU-WEST",
                        "site": "PAR1",
                        "service": "openinfra-api",
                        "tenant_id": "default",
                    },
                }
            ],
            "exactly region, site and service",
        ),
        (
            [
                {
                    "targets": ["par1.example.invalid:443"],
                    "labels": {
                        "region": "EU-WEST",
                        "site": "PAR1",
                        "service": "other",
                    },
                }
            ],
            "service must be openinfra-api",
        ),
    ],
)
def test_multisite_target_file_validator_rejects_unsafe_contracts(
    tmp_path: Path, payload: object, message: str
) -> None:
    target_file = tmp_path / "invalid.json"
    target_file.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(MultisiteObservabilityValidationError, match=message):
        MultisiteTargetFileValidator.validate_file(target_file)
