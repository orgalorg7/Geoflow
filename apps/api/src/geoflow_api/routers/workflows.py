import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from geoflow_api.auth.dependencies import CurrentUser
from geoflow_api.models import Workflow
from geoflow_api.schemas import (
    WorkflowCreate,
    WorkflowDefinitionsResponse,
    WorkflowEdgeResponse,
    WorkflowGraphReplace,
    WorkflowGraphResponse,
    WorkflowNodeResponse,
    WorkflowResponse,
    WorkflowUpdate,
    WorkflowValidationIssue,
    WorkflowValidationResponse,
)
from geoflow_api.workflows.definitions import serialize_definitions
from geoflow_api.workflows.dependencies import get_workflow_service
from geoflow_api.workflows.graph import GraphEdgeSpec, GraphNodeSpec, ValidationResult
from geoflow_api.workflows.service import (
    WorkflowGraphStructureError,
    WorkflowNotFoundError,
    WorkflowService,
)

router = APIRouter(
    prefix="/projects/{project_id}/workflows",
    tags=["workflows"],
)
definitions_router = APIRouter(tags=["workflows"])
WorkflowServiceDependency = Annotated[WorkflowService, Depends(get_workflow_service)]


@definitions_router.get(
    "/workflow-definitions",
    response_model=WorkflowDefinitionsResponse,
)
async def workflow_definitions(_: CurrentUser) -> WorkflowDefinitionsResponse:
    return WorkflowDefinitionsResponse.model_validate(serialize_definitions())


@router.get("", response_model=list[WorkflowResponse])
async def list_workflows(
    project_id: uuid.UUID,
    user: CurrentUser,
    service: WorkflowServiceDependency,
) -> list[Workflow]:
    try:
        return await service.list_workflows(user.id, project_id)
    except WorkflowNotFoundError as exc:
        raise _not_found(exc) from exc


@router.post(
    "",
    response_model=WorkflowResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workflow(
    project_id: uuid.UUID,
    payload: WorkflowCreate,
    user: CurrentUser,
    service: WorkflowServiceDependency,
) -> Workflow:
    try:
        return await service.create_workflow(
            user.id,
            project_id,
            name=payload.name,
            description=payload.description,
        )
    except WorkflowNotFoundError as exc:
        raise _not_found(exc) from exc


@router.get("/{workflow_id}", response_model=WorkflowGraphResponse)
async def get_workflow(
    project_id: uuid.UUID,
    workflow_id: uuid.UUID,
    user: CurrentUser,
    service: WorkflowServiceDependency,
) -> WorkflowGraphResponse:
    try:
        workflow = await service.get_workflow(user.id, project_id, workflow_id)
    except WorkflowNotFoundError as exc:
        raise _not_found(exc) from exc
    return _graph_response(workflow)


@router.patch("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    project_id: uuid.UUID,
    workflow_id: uuid.UUID,
    payload: WorkflowUpdate,
    user: CurrentUser,
    service: WorkflowServiceDependency,
) -> Workflow:
    try:
        return await service.update_workflow(
            user.id,
            project_id,
            workflow_id,
            name=payload.name,
            description=payload.description,
            description_is_set="description" in payload.model_fields_set,
        )
    except WorkflowNotFoundError as exc:
        raise _not_found(exc) from exc


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    project_id: uuid.UUID,
    workflow_id: uuid.UUID,
    user: CurrentUser,
    service: WorkflowServiceDependency,
) -> None:
    try:
        await service.delete_workflow(user.id, project_id, workflow_id)
    except WorkflowNotFoundError as exc:
        raise _not_found(exc) from exc


@router.put("/{workflow_id}/graph", response_model=WorkflowGraphResponse)
async def replace_workflow_graph(
    project_id: uuid.UUID,
    workflow_id: uuid.UUID,
    payload: WorkflowGraphReplace,
    user: CurrentUser,
    service: WorkflowServiceDependency,
) -> WorkflowGraphResponse:
    nodes = [GraphNodeSpec(node.key, node.type, node.config) for node in payload.nodes]
    edges = [
        GraphEdgeSpec(
            edge.source,
            edge.source_port,
            edge.target,
            edge.target_port,
        )
        for edge in payload.edges
    ]
    try:
        workflow = await service.replace_graph(
            user.id,
            project_id,
            workflow_id,
            nodes=nodes,
            edges=edges,
        )
    except WorkflowNotFoundError as exc:
        raise _not_found(exc) from exc
    except WorkflowGraphStructureError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return _graph_response(workflow)


@router.post("/{workflow_id}/validate", response_model=WorkflowValidationResponse)
async def validate_workflow(
    project_id: uuid.UUID,
    workflow_id: uuid.UUID,
    user: CurrentUser,
    service: WorkflowServiceDependency,
) -> WorkflowValidationResponse:
    try:
        result = await service.validate_workflow(user.id, project_id, workflow_id)
    except WorkflowNotFoundError as exc:
        raise _not_found(exc) from exc
    return _validation_response(result)


def _graph_response(workflow: Workflow) -> WorkflowGraphResponse:
    keys_by_id = {node.id: node.node_key for node in workflow.nodes}
    return WorkflowGraphResponse(
        id=workflow.id,
        project_id=workflow.project_id,
        name=workflow.name,
        description=workflow.description,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
        nodes=[
            WorkflowNodeResponse(
                id=node.id,
                key=node.node_key,
                type=node.node_type,
                config=node.config,
            )
            for node in workflow.nodes
        ],
        edges=[
            WorkflowEdgeResponse(
                id=edge.id,
                source=keys_by_id.get(edge.source_node_id, ""),
                source_port=edge.source_port,
                target=keys_by_id.get(edge.target_node_id, ""),
                target_port=edge.target_port,
            )
            for edge in workflow.edges
        ],
    )


def _validation_response(result: ValidationResult) -> WorkflowValidationResponse:
    return WorkflowValidationResponse(
        valid=result.valid,
        executable=result.valid,
        errors=[
            WorkflowValidationIssue(
                code=issue.code,
                message=issue.message,
                node_key=issue.node_key,
                edge_index=issue.edge_index,
            )
            for issue in result.errors
        ],
    )


def _not_found(exc: WorkflowNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
