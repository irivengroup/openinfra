from __future__ import annotations

from pathlib import Path

import pytest
from scripts.validate_openapi import OpenApiValidationError, validate_openapi_document

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_DOCUMENTS = (
    PROJECT_ROOT / "docs/api/openapi.yaml",
    PROJECT_ROOT / "docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0/09-API/OpenAPI/openapi.yaml",
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


def test_openapi_operations_are_grouped_by_component_then_context() -> None:
    from openinfra.interfaces.openapi_taxonomy import OpenApiDocumentationTaxonomy

    expected_components = list(OpenApiDocumentationTaxonomy.component_order())
    expected_tags = list(OpenApiDocumentationTaxonomy.tags())
    for document in OPENAPI_DOCUMENTS:
        parsed = validate_openapi_document(document)
        declared_tags = [item["name"] for item in parsed["tags"]]
        assert declared_tags == expected_tags
        groups = parsed["x-tagGroups"]
        assert [group["name"] for group in groups] == expected_components
        grouped_tags = [tag for group in groups for tag in group["tags"]]
        assert grouped_tags == expected_tags
        assert len(grouped_tags) == len(set(grouped_tags))

        seen_tags: set[str] = set()
        operation_count = 0
        for route, path_item in parsed["paths"].items():
            expected = OpenApiDocumentationTaxonomy.context_for_path(route)
            for method, operation in path_item.items():
                if method.lower() not in {
                    "get",
                    "post",
                    "put",
                    "patch",
                    "delete",
                    "options",
                    "head",
                    "trace",
                }:
                    continue
                operation_count += 1
                assert operation["tags"] == [expected.tag]
                assert operation["x-openinfra-component"] == expected.component
                assert operation["x-openinfra-context"] == expected.context
                seen_tags.add(expected.tag)
        assert operation_count >= 300
        assert seen_tags == set(expected_tags)


def test_openapi_taxonomy_rejects_an_unclassified_path() -> None:
    from openinfra.interfaces.openapi_taxonomy import OpenApiDocumentationTaxonomy

    with pytest.raises(ValueError, match="OpenAPI path is not classified"):
        OpenApiDocumentationTaxonomy.context_for_path("/api/v1/unknown")


def test_swagger_renderer_orders_component_context_tags() -> None:
    from openinfra.interfaces.http_api import ApiDocumentationRenderer

    html = ApiDocumentationRenderer.swagger_html("/openapi.yaml")
    assert "componentOrder" in html
    assert "tagsSorter" in html
    assert "operationsSorter: 'alpha'" in html
    assert "docExpansion: 'none'" in html
    assert "displayOperationId: true" in html
    assert "Plateforme" in html
    assert "Multisite" in html
