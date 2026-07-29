import uuid
from datetime import UTC, datetime

from geoflow_api.models import Project, Workflow
from geoflow_api.workflows.graph import (
    GraphEdgeSpec,
    GraphNodeSpec,
    ValidationResult,
    validate_graph,
)
from geoflow_api.workflows.repository import WorkflowRepository


class WorkflowNotFoundError(ValueError):
    pass


class WorkflowGraphStructureError(ValueError):
    pass


class WorkflowService:
    def __init__(self, repository: WorkflowRepository) -> None:
        self.repository = repository

    async def get_project(self, user_id: uuid.UUID, project_id: uuid.UUID) -> Project:
        project = await self.repository.get_project(project_id)
        if project is None or project.user_id != user_id:
            raise WorkflowNotFoundError("Project not found")
        return project

    async def list_workflows(self, user_id: uuid.UUID, project_id: uuid.UUID) -> list[Workflow]:
        await self.get_project(user_id, project_id)
        return await self.repository.list_workflows(project_id)

    async def get_workflow(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        workflow_id: uuid.UUID,
    ) -> Workflow:
        await self.get_project(user_id, project_id)
        workflow = await self.repository.get_workflow(workflow_id)
        if workflow is None or workflow.project_id != project_id:
            raise WorkflowNotFoundError("Workflow not found")
        return workflow

    async def create_workflow(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        *,
        name: str,
        description: str | None,
    ) -> Workflow:
        await self.get_project(user_id, project_id)
        now = datetime.now(UTC)
        workflow = Workflow(
            id=uuid.uuid4(),
            project_id=project_id,
            name=name,
            description=_clean_description(description),
            created_at=now,
            updated_at=now,
        )
        await self.repository.add_workflow(workflow)
        await self.repository.commit()
        return workflow

    async def update_workflow(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        workflow_id: uuid.UUID,
        *,
        name: str | None,
        description: str | None,
        description_is_set: bool,
    ) -> Workflow:
        workflow = await self.get_workflow(user_id, project_id, workflow_id)
        if name is not None:
            workflow.name = name
        if description_is_set:
            workflow.description = _clean_description(description)
        workflow.updated_at = datetime.now(UTC)
        await self.repository.commit()
        return workflow

    async def delete_workflow(
        self, user_id: uuid.UUID, project_id: uuid.UUID, workflow_id: uuid.UUID
    ) -> None:
        workflow = await self.get_workflow(user_id, project_id, workflow_id)
        await self.repository.delete_workflow(workflow)
        await self.repository.commit()

    async def replace_graph(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        workflow_id: uuid.UUID,
        *,
        nodes: list[GraphNodeSpec],
        edges: list[GraphEdgeSpec],
    ) -> Workflow:
        workflow = await self.get_workflow(user_id, project_id, workflow_id)
        _validate_persistable_graph(nodes, edges)
        await self.repository.replace_graph(workflow, nodes, edges)
        await self.repository.commit()
        refreshed = await self.repository.get_workflow(workflow_id)
        if refreshed is None:
            raise WorkflowNotFoundError("Workflow not found")
        return refreshed

    async def validate_workflow(
        self, user_id: uuid.UUID, project_id: uuid.UUID, workflow_id: uuid.UUID
    ) -> ValidationResult:
        workflow = await self.get_workflow(user_id, project_id, workflow_id)
        node_keys = {node.id: node.node_key for node in workflow.nodes}
        nodes = [
            GraphNodeSpec(node.node_key, node.node_type, node.config) for node in workflow.nodes
        ]
        edges = [
            GraphEdgeSpec(
                source=node_keys.get(edge.source_node_id, ""),
                source_port=edge.source_port,
                target=node_keys.get(edge.target_node_id, ""),
                target_port=edge.target_port,
            )
            for edge in workflow.edges
        ]
        aoi_ids = await self.repository.list_project_aoi_ids(project_id)
        return validate_graph(nodes, edges, project_aoi_ids=aoi_ids)


def _clean_description(description: str | None) -> str | None:
    if description is None:
        return None
    cleaned = description.strip()
    return cleaned or None


def _validate_persistable_graph(nodes: list[GraphNodeSpec], edges: list[GraphEdgeSpec]) -> None:
    node_keys = [node.key for node in nodes]
    if len(node_keys) != len(set(node_keys)):
        raise WorkflowGraphStructureError("Workflow node keys must be unique")
    known_keys = set(node_keys)
    target_inputs: set[tuple[str, str]] = set()
    for edge in edges:
        if edge.source not in known_keys or edge.target not in known_keys:
            raise WorkflowGraphStructureError(
                "Every edge must reference nodes included in the graph"
            )
        target_input = (edge.target, edge.target_port)
        if target_input in target_inputs:
            raise WorkflowGraphStructureError(
                f"Input '{edge.target}.{edge.target_port}' has multiple connections"
            )
        target_inputs.add(target_input)
