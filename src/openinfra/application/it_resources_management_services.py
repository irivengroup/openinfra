from __future__ import annotations

from openinfra.application.source_of_truth_services import (
    CreateSourceRelationCommand,
    GetSourceObjectCommand,
    GetSourceObjectVersionCommand,
    ListSourceObjectsCommand,
    ListSourceRelationsCommand,
    ListSourceRelationsCommand as ListITResourcesRelationsCommand,
    ListSourceObjectsCommand as ListITResourcesCommand,
    SourceOfTruthService,
    UpsertSourceObjectCommand,
)

ITResourcesManagementService = SourceOfTruthService
UpsertITResourceCommand = UpsertSourceObjectCommand
GetITResourceCommand = GetSourceObjectCommand
GetITResourceVersionCommand = GetSourceObjectVersionCommand
CreateITResourceRelationCommand = CreateSourceRelationCommand

__all__ = [
    "CreateITResourceRelationCommand",
    "CreateSourceRelationCommand",
    "GetITResourceCommand",
    "GetITResourceVersionCommand",
    "GetSourceObjectCommand",
    "GetSourceObjectVersionCommand",
    "ITResourcesManagementService",
    "ListITResourcesCommand",
    "ListITResourcesRelationsCommand",
    "ListSourceObjectsCommand",
    "ListSourceRelationsCommand",
    "SourceOfTruthService",
    "UpsertITResourceCommand",
    "UpsertSourceObjectCommand",
]
