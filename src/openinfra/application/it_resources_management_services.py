from __future__ import annotations

from openinfra.application.source_of_truth_services import (
    CreateSourceRelationCommand,
    GetSourceObjectAsOfCommand,
    GetSourceObjectCommand,
    GetSourceObjectVersionCommand,
    ListSourceObjectAuditCommand,
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
GetITResourceAsOfCommand = GetSourceObjectAsOfCommand
ListITResourceAuditCommand = ListSourceObjectAuditCommand
CreateITResourceRelationCommand = CreateSourceRelationCommand

__all__ = [
    "CreateITResourceRelationCommand",
    "CreateSourceRelationCommand",
    "GetITResourceAsOfCommand",
    "GetITResourceCommand",
    "GetITResourceVersionCommand",
    "GetSourceObjectAsOfCommand",
    "GetSourceObjectCommand",
    "GetSourceObjectVersionCommand",
    "ITResourcesManagementService",
    "ListITResourceAuditCommand",
    "ListITResourcesCommand",
    "ListITResourcesRelationsCommand",
    "ListSourceObjectAuditCommand",
    "ListSourceObjectsCommand",
    "ListSourceRelationsCommand",
    "SourceOfTruthService",
    "UpsertITResourceCommand",
    "UpsertSourceObjectCommand",
]
