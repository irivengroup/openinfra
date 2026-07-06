from __future__ import annotations

from openinfra.application.source_of_truth_services import (
    CreateSourceRelationCommand,
    GetSourceObjectCommand,
    GetSourceObjectVersionCommand,
    ListSourceObjectsCommand,
    ListSourceRelationsCommand,
    SourceOfTruthService,
    UpsertSourceObjectCommand,
)
from openinfra.application.source_of_truth_services import (
    ListSourceObjectsCommand as ListITResourcesCommand,
)
from openinfra.application.source_of_truth_services import (
    ListSourceRelationsCommand as ListITResourcesRelationsCommand,
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
