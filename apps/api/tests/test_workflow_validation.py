import uuid
from copy import deepcopy

import pytest

from geoflow_api.workflows.graph import (
    GraphEdgeSpec,
    GraphNodeSpec,
    validate_graph,
)


def valid_graph(aoi_id: uuid.UUID) -> tuple[list[GraphNodeSpec], list[GraphEdgeSpec]]:
    nodes = [
        GraphNodeSpec("aoi", "aoi", {"aoi_id": str(aoi_id)}),
        GraphNodeSpec(
            "dataset",
            "dataset",
            {
                "dataset": "sentinel-2-l2a",
                "date_from": "2026-06-01",
                "date_to": "2026-06-30",
                "cloud_cover_max": 20,
            },
        ),
        GraphNodeSpec(
            "operation",
            "operation",
            {"operation": "ndvi", "parameters": {}},
        ),
        GraphNodeSpec(
            "visualization",
            "visualization",
            {"color_ramp": "rdylgn", "min": -1, "max": 1, "opacity": 0.8},
        ),
    ]
    edges = [
        GraphEdgeSpec("aoi", "geometry", "dataset", "aoi"),
        GraphEdgeSpec("aoi", "geometry", "operation", "aoi"),
        GraphEdgeSpec("dataset", "raster", "operation", "raster"),
        GraphEdgeSpec("operation", "raster", "visualization", "raster"),
    ]
    return nodes, edges


def issue_codes(
    nodes: list[GraphNodeSpec],
    edges: list[GraphEdgeSpec],
    aoi_id: uuid.UUID,
) -> set[str]:
    result = validate_graph(nodes, edges, project_aoi_ids={aoi_id})
    assert result.valid is False
    return {issue.code for issue in result.errors}


def test_valid_ndvi_graph_is_executable() -> None:
    aoi_id = uuid.uuid4()
    nodes, edges = valid_graph(aoi_id)

    result = validate_graph(nodes, edges, project_aoi_ids={aoi_id})

    assert result.valid is True
    assert result.errors == ()


@pytest.mark.parametrize(
    ("mutate", "expected_code"),
    [
        (
            lambda nodes, edges: edges.pop(),
            "missing_input",
        ),
        (
            lambda nodes, edges: nodes.__setitem__(
                0, GraphNodeSpec("aoi", "aoi", {"aoi_id": str(uuid.uuid4())})
            ),
            "missing_aoi",
        ),
        (
            lambda nodes, edges: nodes.__setitem__(
                1,
                GraphNodeSpec(
                    "dataset",
                    "dataset",
                    {
                        "dataset": "sentinel-2-l2a",
                        "date_from": "2026-07-01",
                        "date_to": "2026-06-01",
                        "cloud_cover_max": 20,
                    },
                ),
            ),
            "invalid_dates",
        ),
        (
            lambda nodes, edges: edges.append(
                GraphEdgeSpec("visualization", "preview", "aoi", "geometry")
            ),
            "cyclic_dependency",
        ),
        (
            lambda nodes, edges: edges.__setitem__(
                3,
                GraphEdgeSpec("dataset", "raster", "visualization", "raster"),
            ),
            "unsupported_connection",
        ),
        (
            lambda nodes, edges: nodes.__setitem__(
                1,
                GraphNodeSpec(
                    "dataset",
                    "dataset",
                    {
                        "dataset": "unknown-satellite",
                        "date_from": "2026-06-01",
                        "date_to": "2026-06-30",
                        "cloud_cover_max": 20,
                    },
                ),
            ),
            "unsupported_dataset",
        ),
        (
            lambda nodes, edges: nodes.__setitem__(
                1,
                GraphNodeSpec(
                    "dataset",
                    "dataset",
                    {
                        "dataset": "sentinel-2-l2a",
                        "date_from": "2026-06-01",
                        "date_to": "2026-06-30",
                        "cloud_cover_max": 20,
                        "bands": ["red"],
                    },
                ),
            ),
            "unsupported_band",
        ),
        (
            lambda nodes, edges: nodes.__setitem__(
                2,
                GraphNodeSpec(
                    "operation",
                    "operation",
                    {
                        "operation": "ndvi",
                        "parameters": {"unsupported_threshold": 2},
                    },
                ),
            ),
            "invalid_parameter",
        ),
    ],
)
def test_invalid_graphs_report_actionable_errors(mutate, expected_code: str) -> None:
    aoi_id = uuid.uuid4()
    original_nodes, original_edges = valid_graph(aoi_id)
    nodes = deepcopy(original_nodes)
    edges = deepcopy(original_edges)

    mutate(nodes, edges)

    assert expected_code in issue_codes(nodes, edges, aoi_id)


def test_cloud_cover_and_visualization_values_are_bounded() -> None:
    aoi_id = uuid.uuid4()
    nodes, edges = valid_graph(aoi_id)
    nodes[1] = GraphNodeSpec(
        "dataset",
        "dataset",
        {
            "dataset": "sentinel-2-l2a",
            "date_from": "2026-06-01",
            "date_to": "2026-06-30",
            "cloud_cover_max": 140,
        },
    )
    nodes[3] = GraphNodeSpec(
        "visualization",
        "visualization",
        {"color_ramp": "unknown", "min": 1, "max": -1, "opacity": 2},
    )

    codes = issue_codes(nodes, edges, aoi_id)

    assert codes == {"invalid_parameter"}
