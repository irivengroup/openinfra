from __future__ import annotations

from pathlib import Path

import pytest
from scripts.validate_openapi import OpenApiValidationError, validate_openapi_document

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_DOCUMENTS = (
    PROJECT_ROOT / "docs/api/openapi.yaml",
    PROJECT_ROOT / "docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/09-API/OpenAPI/openapi.yaml",
)


def test_openapi_documents_have_unique_yaml_keys_and_supported_versions() -> None:
    for document in OPENAPI_DOCUMENTS:
        parsed = validate_openapi_document(document)
        assert parsed["openapi"].startswith("3.")
        assert parsed["paths"]


def test_duplicate_yaml_mapping_key_is_rejected(tmp_path: Path) -> None:
    document = tmp_path / "duplicate.yaml"
    document.write_text(
        "openapi: 3.1.0\ninfo: {title: test, version: '1'}\npaths:\n"
        "  /v1/items: {get: {responses: {'200': {description: ok}}}}\n"
        "  /v1/items: {post: {responses: {'201': {description: created}}}}\n",
        encoding="utf-8",
    )

    with pytest.raises(OpenApiValidationError, match=r"duplicate key.*?/v1/items"):
        validate_openapi_document(document)


def test_missing_openapi_version_is_rejected(tmp_path: Path) -> None:
    document = tmp_path / "missing-version.yaml"
    document.write_text("info: {title: test, version: '1'}\npaths: {}\n", encoding="utf-8")

    with pytest.raises(OpenApiValidationError, match="unsupported or missing OpenAPI version"):
        validate_openapi_document(document)
