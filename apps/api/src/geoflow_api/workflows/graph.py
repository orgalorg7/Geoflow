import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import date
from typing import Any

from geoflow_api.workflows.definitions import (
    DATASET_DEFINITIONS,
    NODE_DEFINITIONS,
    OPERATION_DEFINITIONS,
    SUPPORTED_CONNECTIONS,
    VISUALIZATION_RAMPS,
)


@dataclass(frozen=True)
class GraphNodeSpec:
    key: str
    type: str
    config: dict[str, Any]


@dataclass(frozen=True)
class GraphEdgeSpec:
    source: str
    source_port: str
    target: str
    target_port: str


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    node_key: str | None = None
    edge_index: int | None = None


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: tuple[ValidationIssue, ...]


def validate_graph(
    nodes: list[GraphNodeSpec],
    edges: list[GraphEdgeSpec],
    *,
    project_aoi_ids: set[uuid.UUID],
) -> ValidationResult:
    errors: list[ValidationIssue] = []
    nodes_by_key: dict[str, GraphNodeSpec] = {}

    for node in nodes:
        if node.key in nodes_by_key:
            errors.append(
                ValidationIssue(
                    "duplicate_node_key",
                    f"Node key '{node.key}' is used more than once",
                    node_key=node.key,
                )
            )
            continue
        nodes_by_key[node.key] = node
        if node.type not in NODE_DEFINITIONS:
            errors.append(
                ValidationIssue(
                    "unsupported_node_type",
                    f"Node type '{node.type}' is not supported",
                    node_key=node.key,
                )
            )

    for required_type in NODE_DEFINITIONS:
        if not any(node.type == required_type for node in nodes):
            errors.append(
                ValidationIssue(
                    "missing_node",
                    f"Workflow requires at least one {required_type} node",
                )
            )

    valid_edges: list[GraphEdgeSpec] = []
    target_inputs: set[tuple[str, str]] = set()
    adjacency: dict[str, list[str]] = defaultdict(list)
    indegree = {key: 0 for key in nodes_by_key}

    for index, edge in enumerate(edges):
        source = nodes_by_key.get(edge.source)
        target = nodes_by_key.get(edge.target)
        if source is None or target is None:
            errors.append(
                ValidationIssue(
                    "unknown_node",
                    "Edge references a node key that does not exist",
                    edge_index=index,
                )
            )
            continue

        adjacency[source.key].append(target.key)
        indegree[target.key] += 1

        target_input = (target.key, edge.target_port)
        if target_input in target_inputs:
            errors.append(
                ValidationIssue(
                    "duplicate_input",
                    f"Input '{target.key}.{edge.target_port}' has multiple connections",
                    node_key=target.key,
                    edge_index=index,
                )
            )
            continue
        target_inputs.add(target_input)

        connection = (
            source.type,
            edge.source_port,
            target.type,
            edge.target_port,
        )
        if connection not in SUPPORTED_CONNECTIONS:
            errors.append(
                ValidationIssue(
                    "unsupported_connection",
                    f"Connection {source.type}.{edge.source_port} → "
                    f"{target.type}.{edge.target_port} is not supported",
                    edge_index=index,
                )
            )
            continue
        valid_edges.append(edge)

    _validate_cycles(nodes_by_key, adjacency, indegree, errors)
    _validate_required_inputs(nodes, valid_edges, errors)

    dataset_bands: dict[str, set[str]] = {}
    for node in nodes:
        if node.type == "aoi":
            _validate_aoi_node(node, project_aoi_ids, errors)
        elif node.type == "dataset":
            selected = _validate_dataset_node(node, errors)
            if selected is not None:
                dataset_bands[node.key] = selected
        elif node.type == "visualization":
            _validate_visualization_node(node, errors)

    for node in nodes:
        if node.type == "operation":
            _validate_operation_node(node, valid_edges, dataset_bands, errors)

    return ValidationResult(valid=not errors, errors=tuple(errors))


def _validate_cycles(
    nodes_by_key: dict[str, GraphNodeSpec],
    adjacency: dict[str, list[str]],
    indegree: dict[str, int],
    errors: list[ValidationIssue],
) -> None:
    queue = deque(key for key, count in indegree.items() if count == 0)
    visited = 0
    while queue:
        key = queue.popleft()
        visited += 1
        for target in adjacency[key]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if visited != len(nodes_by_key):
        errors.append(
            ValidationIssue(
                "cyclic_dependency",
                "Workflow graph contains a cyclic dependency",
            )
        )


def _validate_required_inputs(
    nodes: list[GraphNodeSpec],
    edges: list[GraphEdgeSpec],
    errors: list[ValidationIssue],
) -> None:
    connected = {(edge.target, edge.target_port) for edge in edges}
    for node in nodes:
        definition = NODE_DEFINITIONS.get(node.type)
        if definition is None:
            continue
        for required_input in definition.required_inputs:
            if (node.key, required_input) not in connected:
                errors.append(
                    ValidationIssue(
                        "missing_input",
                        f"Node '{node.key}' requires input '{required_input}'",
                        node_key=node.key,
                    )
                )


def _validate_aoi_node(
    node: GraphNodeSpec,
    project_aoi_ids: set[uuid.UUID],
    errors: list[ValidationIssue],
) -> None:
    raw_aoi_id = node.config.get("aoi_id")
    try:
        aoi_id = uuid.UUID(str(raw_aoi_id))
    except (ValueError, TypeError, AttributeError):
        errors.append(
            ValidationIssue(
                "missing_aoi",
                "AOI node must reference a valid area of interest",
                node_key=node.key,
            )
        )
        return
    if aoi_id not in project_aoi_ids:
        errors.append(
            ValidationIssue(
                "missing_aoi",
                "Selected area of interest does not belong to this project",
                node_key=node.key,
            )
        )


def _validate_dataset_node(node: GraphNodeSpec, errors: list[ValidationIssue]) -> set[str] | None:
    dataset_id = node.config.get("dataset")
    definition = DATASET_DEFINITIONS.get(dataset_id)
    if definition is None:
        errors.append(
            ValidationIssue(
                "unsupported_dataset",
                f"Dataset '{dataset_id}' is not supported",
                node_key=node.key,
            )
        )
        return None

    date_from = _parse_date(node.config.get("date_from"))
    date_to = _parse_date(node.config.get("date_to"))
    if date_from is None or date_to is None or date_from > date_to:
        errors.append(
            ValidationIssue(
                "invalid_dates",
                "Dataset date range must contain valid dates in chronological order",
                node_key=node.key,
            )
        )

    cloud_cover = node.config.get("cloud_cover_max")
    if (
        isinstance(cloud_cover, bool)
        or not isinstance(cloud_cover, (int, float))
        or not 0 <= cloud_cover <= 100
    ):
        errors.append(
            ValidationIssue(
                "invalid_parameter",
                "Cloud-cover limit must be between 0 and 100",
                node_key=node.key,
            )
        )

    configured_bands = node.config.get("bands")
    if configured_bands is None:
        return set(definition.bands)
    if not isinstance(configured_bands, list) or not all(
        isinstance(band, str) for band in configured_bands
    ):
        errors.append(
            ValidationIssue(
                "unsupported_band",
                "Dataset bands must be a list of band names",
                node_key=node.key,
            )
        )
        return None
    unsupported = set(configured_bands) - set(definition.bands)
    if unsupported:
        errors.append(
            ValidationIssue(
                "unsupported_band",
                f"Dataset does not provide bands: {', '.join(sorted(unsupported))}",
                node_key=node.key,
            )
        )
    return set(configured_bands)


def _validate_operation_node(
    node: GraphNodeSpec,
    edges: list[GraphEdgeSpec],
    dataset_bands: dict[str, set[str]],
    errors: list[ValidationIssue],
) -> None:
    operation_id = node.config.get("operation")
    definition = OPERATION_DEFINITIONS.get(operation_id)
    if definition is None:
        errors.append(
            ValidationIssue(
                "unsupported_operation",
                f"Operation '{operation_id}' is not supported",
                node_key=node.key,
            )
        )
        return

    parameters = node.config.get("parameters", {})
    if not isinstance(parameters, dict):
        errors.append(
            ValidationIssue(
                "invalid_parameter",
                "Operation parameters must be an object",
                node_key=node.key,
            )
        )
        return
    unsupported_parameters = set(parameters) - set(definition.parameters)
    if unsupported_parameters:
        errors.append(
            ValidationIssue(
                "invalid_parameter",
                f"Unsupported parameters: {', '.join(sorted(unsupported_parameters))}",
                node_key=node.key,
            )
        )
    for parameter, rules in definition.parameters.items():
        value = parameters.get(parameter, rules.get("default"))
        if rules["type"] == "number" and (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or value < rules["minimum"]
            or value > rules["maximum"]
        ):
            errors.append(
                ValidationIssue(
                    "invalid_parameter",
                    f"Parameter '{parameter}' must be between "
                    f"{rules['minimum']} and {rules['maximum']}",
                    node_key=node.key,
                )
            )

    dataset_edge = next(
        (edge for edge in edges if edge.target == node.key and edge.target_port == "raster"),
        None,
    )
    if dataset_edge is None:
        return
    selected_bands = dataset_bands.get(dataset_edge.source)
    if selected_bands is None:
        return
    missing_bands = set(definition.required_bands) - selected_bands
    if missing_bands:
        errors.append(
            ValidationIssue(
                "unsupported_band",
                f"Operation requires unavailable bands: {', '.join(sorted(missing_bands))}",
                node_key=node.key,
            )
        )


def _validate_visualization_node(node: GraphNodeSpec, errors: list[ValidationIssue]) -> None:
    allowed_ramps = {ramp["id"] for ramp in VISUALIZATION_RAMPS}
    ramp = node.config.get("color_ramp")
    if ramp not in allowed_ramps:
        errors.append(
            ValidationIssue(
                "invalid_parameter",
                f"Visualization color ramp '{ramp}' is not supported",
                node_key=node.key,
            )
        )
    minimum = node.config.get("min")
    maximum = node.config.get("max")
    if (
        isinstance(minimum, bool)
        or isinstance(maximum, bool)
        or not isinstance(minimum, (int, float))
        or not isinstance(maximum, (int, float))
        or minimum >= maximum
    ):
        errors.append(
            ValidationIssue(
                "invalid_parameter",
                "Visualization minimum must be lower than maximum",
                node_key=node.key,
            )
        )
    opacity = node.config.get("opacity", 1.0)
    if isinstance(opacity, bool) or not isinstance(opacity, (int, float)) or not 0 <= opacity <= 1:
        errors.append(
            ValidationIssue(
                "invalid_parameter",
                "Visualization opacity must be between 0 and 1",
                node_key=node.key,
            )
        )


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
