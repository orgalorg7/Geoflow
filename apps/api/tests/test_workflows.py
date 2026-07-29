import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from geoflow_api.auth.dependencies import get_current_user
from geoflow_api.main import app
from geoflow_api.models import (
    AreaOfInterest,
    Project,
    User,
    Workflow,
    WorkflowEdge,
    WorkflowNode,
)
from geoflow_api.workflows.dependencies import get_workflow_service
from geoflow_api.workflows.graph import GraphEdgeSpec, GraphNodeSpec
from geoflow_api.workflows.repository import WorkflowRepository
from geoflow_api.workflows.service import WorkflowService


class InMemoryWorkflowRepository(WorkflowRepository):
    def __init__(self) -> None:
        self.projects: dict[uuid.UUID, Project] = {}
        self.aois: dict[uuid.UUID, AreaOfInterest] = {}
        self.workflows: dict[uuid.UUID, Workflow] = {}

    async def get_project(self, project_id: uuid.UUID) -> Project | None:
        return self.projects.get(project_id)

    async def list_project_aoi_ids(self, project_id: uuid.UUID) -> set[uuid.UUID]:
        return {aoi.id for aoi in self.aois.values() if aoi.project_id == project_id}

    async def list_workflows(self, project_id: uuid.UUID) -> list[Workflow]:
        return [
            workflow for workflow in self.workflows.values() if workflow.project_id == project_id
        ]

    async def get_workflow(self, workflow_id: uuid.UUID) -> Workflow | None:
        return self.workflows.get(workflow_id)

    async def add_workflow(self, workflow: Workflow) -> None:
        workflow.nodes = []
        workflow.edges = []
        self.workflows[workflow.id] = workflow

    async def delete_workflow(self, workflow: Workflow) -> None:
        self.workflows.pop(workflow.id, None)

    async def replace_graph(
        self,
        workflow: Workflow,
        nodes: list[GraphNodeSpec],
        edges: list[GraphEdgeSpec],
    ) -> None:
        persisted_nodes = [
            WorkflowNode(
                id=uuid.uuid4(),
                workflow_id=workflow.id,
                node_key=node.key,
                node_type=node.type,
                config=node.config,
            )
            for node in nodes
        ]
        nodes_by_key = {node.node_key: node for node in persisted_nodes}
        persisted_edges = [
            WorkflowEdge(
                id=uuid.uuid4(),
                workflow_id=workflow.id,
                source_node_id=nodes_by_key[edge.source].id,
                source_port=edge.source_port,
                target_node_id=nodes_by_key[edge.target].id,
                target_port=edge.target_port,
            )
            for edge in edges
        ]
        workflow.nodes = persisted_nodes
        workflow.edges = persisted_edges
        workflow.updated_at = datetime.now(UTC)

    async def commit(self) -> None:
        pass


def make_user(email: str) -> User:
    now = datetime.now(UTC)
    return User(
        id=uuid.uuid4(),
        email=email,
        full_name="Workflow Owner",
        password_hash="not-used",
        role="user",
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def make_project(user_id: uuid.UUID) -> Project:
    now = datetime.now(UTC)
    return Project(
        id=uuid.uuid4(),
        user_id=user_id,
        name="Nile Delta",
        description=None,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_workflow_api_saves_validates_and_protects_graph() -> None:
    repository = InMemoryWorkflowRepository()
    service = WorkflowService(repository)
    owner = make_user("workflow-owner@example.com")
    other_user = make_user("workflow-other@example.com")
    project = make_project(owner.id)
    aoi_id = uuid.uuid4()
    repository.projects[project.id] = project
    active_user = {"value": owner}

    async def override_user() -> User:
        return active_user["value"]

    async def override_service() -> WorkflowService:
        return service

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_workflow_service] = override_service
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            definitions = await client.get("/api/v1/workflow-definitions")
            created = await client.post(
                f"/api/v1/projects/{project.id}/workflows",
                json={"name": "June NDVI", "description": "Vegetation health"},
            )
            assert definitions.status_code == 200
            assert [item["id"] for item in definitions.json()["datasets"]] == ["sentinel-2-l2a"]
            assert [item["id"] for item in definitions.json()["operations"]] == ["ndvi"]
            assert created.status_code == 201
            workflow_id = created.json()["id"]

            graph = _graph_payload(aoi_id)
            repository.aois[aoi_id] = _aoi(project.id, aoi_id)
            saved = await client.put(
                f"/api/v1/projects/{project.id}/workflows/{workflow_id}/graph",
                json=graph,
            )
            validation = await client.post(
                f"/api/v1/projects/{project.id}/workflows/{workflow_id}/validate"
            )
            assert saved.status_code == 200
            assert len(saved.json()["nodes"]) == 4
            assert len(saved.json()["edges"]) == 4
            assert validation.status_code == 200
            assert validation.json() == {
                "valid": True,
                "executable": True,
                "errors": [],
            }

            active_user["value"] = other_user
            protected = await client.get(f"/api/v1/projects/{project.id}/workflows/{workflow_id}")
            assert protected.status_code == 404
    finally:
        app.dependency_overrides.clear()


def _aoi(project_id: uuid.UUID, aoi_id: uuid.UUID) -> AreaOfInterest:
    now = datetime.now(UTC)
    return AreaOfInterest(
        id=aoi_id,
        project_id=project_id,
        name="Delta farms",
        geometry="not-used",
        area_sq_km=12.5,
        created_at=now,
        updated_at=now,
    )


def _graph_payload(aoi_id: uuid.UUID) -> dict[str, object]:
    return {
        "nodes": [
            {"key": "aoi", "type": "aoi", "config": {"aoi_id": str(aoi_id)}},
            {
                "key": "dataset",
                "type": "dataset",
                "config": {
                    "dataset": "sentinel-2-l2a",
                    "date_from": "2026-06-01",
                    "date_to": "2026-06-30",
                    "cloud_cover_max": 20,
                },
            },
            {
                "key": "operation",
                "type": "operation",
                "config": {"operation": "ndvi", "parameters": {}},
            },
            {
                "key": "visualization",
                "type": "visualization",
                "config": {
                    "color_ramp": "rdylgn",
                    "min": -1,
                    "max": 1,
                    "opacity": 0.8,
                },
            },
        ],
        "edges": [
            {
                "source": "aoi",
                "source_port": "geometry",
                "target": "dataset",
                "target_port": "aoi",
            },
            {
                "source": "aoi",
                "source_port": "geometry",
                "target": "operation",
                "target_port": "aoi",
            },
            {
                "source": "dataset",
                "source_port": "raster",
                "target": "operation",
                "target_port": "raster",
            },
            {
                "source": "operation",
                "source_port": "raster",
                "target": "visualization",
                "target_port": "raster",
            },
        ],
    }
