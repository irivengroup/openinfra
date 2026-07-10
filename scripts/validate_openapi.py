#!/usr/bin/env python3
"""Validate OpenAPI YAML documents and reject duplicate mapping keys."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode


class OpenApiValidationError(ValueError):
    """Raised when an OpenAPI document is malformed or unsupported."""


class UniqueKeySafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate keys at every mapping level."""


def _construct_unique_mapping(
    loader: UniqueKeySafeLoader,
    node: MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable mapping key",
                key_node.start_mark,
            ) from exc
        if duplicate:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def validate_openapi_document(path: Path) -> dict[str, Any]:
    """Load and validate the minimum structural OpenAPI contract."""
    try:
        document = yaml.load(
            path.read_text(encoding="utf-8"),
            Loader=UniqueKeySafeLoader,  # noqa: S506 -- subclasses SafeLoader
        )
    except (OSError, yaml.YAMLError) as exc:
        raise OpenApiValidationError(f"{path}: invalid YAML: {exc}") from exc
    if not isinstance(document, dict):
        raise OpenApiValidationError(f"{path}: root document must be a mapping")
    version = document.get("openapi")
    if not isinstance(version, str) or not version.startswith(("3.0.", "3.1.", "3.2.")):
        raise OpenApiValidationError(
            f"{path}: unsupported or missing OpenAPI version; "
            "expected openapi: 3.0.x, 3.1.x or 3.2.x"
        )
    paths = document.get("paths")
    if not isinstance(paths, dict):
        raise OpenApiValidationError(f"{path}: paths must be a mapping")
    components = document.get("components", {})
    if not isinstance(components, dict):
        raise OpenApiValidationError(f"{path}: components must be a mapping when present")
    return document


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate OpenAPI YAML syntax, unique keys and required structure."
    )
    parser.add_argument("documents", nargs="+", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        for document in args.documents:
            validate_openapi_document(document)
            print(f"OpenAPI OK: {document}")
    except OpenApiValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
