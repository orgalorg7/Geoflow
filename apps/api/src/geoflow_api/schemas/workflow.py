import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2_000)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return _clean_name(value)


class WorkflowUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2_000)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        return _clean_name(value) if value is not None else None


class WorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class WorkflowNodeInput(BaseModel):
    key: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_-]*$",
    )
    type: str = Field(min_length=1, max_length=32)
    config: dict[str, Any] = Field(default_factory=dict)


class WorkflowEdgeInput(BaseModel):
    source: str = Field(min_length=1, max_length=64)
    source_port: str = Field(min_length=1, max_length=32)
    target: str = Field(min_length=1, max_length=64)
    target_port: str = Field(min_length=1, max_length=32)


class WorkflowGraphReplace(BaseModel):
    nodes: list[WorkflowNodeInput] = Field(max_length=100)
    edges: list[WorkflowEdgeInput] = Field(max_length=300)


class WorkflowNodeResponse(WorkflowNodeInput):
    id: uuid.UUID


class WorkflowEdgeResponse(WorkflowEdgeInput):
    id: uuid.UUID


class WorkflowGraphResponse(WorkflowResponse):
    nodes: list[WorkflowNodeResponse]
    edges: list[WorkflowEdgeResponse]


class WorkflowValidationIssue(BaseModel):
    code: str
    message: str
    node_key: str | None
    edge_index: int | None


class WorkflowValidationResponse(BaseModel):
    valid: bool
    executable: bool
    errors: list[WorkflowValidationIssue]


class WorkflowNodeDefinitionResponse(BaseModel):
    type: str
    label: str
    required_inputs: list[str]
    outputs: list[str]


class WorkflowDatasetDefinitionResponse(BaseModel):
    id: str
    label: str
    bands: list[str]


class WorkflowOperationDefinitionResponse(BaseModel):
    id: str
    label: str
    required_bands: list[str]
    parameters: dict[str, dict[str, Any]]


class WorkflowVisualizationRampResponse(BaseModel):
    id: str
    label: str


class WorkflowConnectionDefinitionResponse(BaseModel):
    source_type: str
    source_port: str
    target_type: str
    target_port: str


class WorkflowDefinitionsResponse(BaseModel):
    node_types: list[WorkflowNodeDefinitionResponse]
    datasets: list[WorkflowDatasetDefinitionResponse]
    operations: list[WorkflowOperationDefinitionResponse]
    visualization_ramps: list[WorkflowVisualizationRampResponse]
    connections: list[WorkflowConnectionDefinitionResponse]


def _clean_name(value: str) -> str:
    cleaned = " ".join(value.split())
    if len(cleaned) < 2:
        raise ValueError("Name must contain at least 2 characters")
    return cleaned
