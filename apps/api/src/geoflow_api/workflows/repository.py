import uuid
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from geoflow_api.models import (
    AreaOfInterest,
    Project,
    Workflow,
    WorkflowEdge,
    WorkflowNode,
)
from geoflow_api.workflows.graph import GraphEdgeSpec, GraphNodeSpec


class WorkflowRepository(Protocol):
    async def get_project(self, project_id: uuid.UUID) -> Project | None: ...

    async def list_project_aoi_ids(self, project_id: uuid.UUID) -> set[uuid.UUID]: ...

    async def list_workflows(self, project_id: uuid.UUID) -> list[Workflow]: ...

    async def get_workflow(self, workflow_id: uuid.UUID) -> Workflow | None: ...

    async def add_workflow(self, workflow: Workflow) -> None: ...

    async def delete_workflow(self, workflow: Workflow) -> None: ...

    async def replace_graph(
        self,
        workflow: Workflow,
        nodes: list[GraphNodeSpec],
        edges: list[GraphEdgeSpec],
    ) -> None: ...

    async def commit(self) -> None: ...


class SqlAlchemyWorkflowRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_project(self, project_id: uuid.UUID) -> Project | None:
        return await self.session.get(Project, project_id)

    async def list_project_aoi_ids(self, project_id: uuid.UUID) -> set[uuid.UUID]:
        result = await self.session.execute(
            select(AreaOfInterest.id).where(AreaOfInterest.project_id == project_id)
        )
        return set(result.scalars())

    async def list_workflows(self, project_id: uuid.UUID) -> list[Workflow]:
        result = await self.session.execute(
            select(Workflow)
            .where(Workflow.project_id == project_id)
            .order_by(Workflow.updated_at.desc())
        )
        return list(result.scalars())

    async def get_workflow(self, workflow_id: uuid.UUID) -> Workflow | None:
        result = await self.session.execute(
            select(Workflow)
            .options(
                selectinload(Workflow.nodes),
                selectinload(Workflow.edges),
            )
            .where(Workflow.id == workflow_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def add_workflow(self, workflow: Workflow) -> None:
        self.session.add(workflow)

    async def delete_workflow(self, workflow: Workflow) -> None:
        await self.session.delete(workflow)

    async def replace_graph(
        self,
        workflow: Workflow,
        nodes: list[GraphNodeSpec],
        edges: list[GraphEdgeSpec],
    ) -> None:
        await self.session.execute(
            delete(WorkflowEdge).where(WorkflowEdge.workflow_id == workflow.id)
        )
        await self.session.execute(
            delete(WorkflowNode).where(WorkflowNode.workflow_id == workflow.id)
        )
        await self.session.flush()

        nodes_by_key: dict[str, WorkflowNode] = {}
        for spec in nodes:
            node = WorkflowNode(
                id=uuid.uuid4(),
                workflow_id=workflow.id,
                node_key=spec.key,
                node_type=spec.type,
                config=spec.config,
            )
            nodes_by_key[spec.key] = node
            self.session.add(node)
        await self.session.flush()

        for spec in edges:
            source = nodes_by_key.get(spec.source)
            target = nodes_by_key.get(spec.target)
            if source is None or target is None:
                continue
            self.session.add(
                WorkflowEdge(
                    id=uuid.uuid4(),
                    workflow_id=workflow.id,
                    source_node_id=source.id,
                    source_port=spec.source_port,
                    target_node_id=target.id,
                    target_port=spec.target_port,
                )
            )
        workflow.updated_at = datetime.now(UTC)

    async def commit(self) -> None:
        await self.session.commit()
