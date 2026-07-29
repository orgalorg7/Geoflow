from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class NodeDefinition:
    type: str
    label: str
    required_inputs: tuple[str, ...]
    outputs: tuple[str, ...]


@dataclass(frozen=True)
class DatasetDefinition:
    id: str
    label: str
    bands: tuple[str, ...]


@dataclass(frozen=True)
class OperationDefinition:
    id: str
    label: str
    required_bands: tuple[str, ...]
    parameters: dict[str, dict[str, Any]]


NODE_DEFINITIONS = {
    "aoi": NodeDefinition("aoi", "Area of interest", (), ("geometry",)),
    "dataset": NodeDefinition("dataset", "Satellite dataset", ("aoi",), ("raster",)),
    "operation": NodeDefinition("operation", "Analysis operation", ("raster", "aoi"), ("raster",)),
    "visualization": NodeDefinition("visualization", "Visualization", ("raster",), ("preview",)),
}

DATASET_DEFINITIONS = {
    "sentinel-2-l2a": DatasetDefinition(
        "sentinel-2-l2a",
        "Sentinel-2 Level-2A",
        ("blue", "green", "red", "nir", "swir1", "swir2"),
    ),
}

OPERATION_DEFINITIONS = {
    "ndvi": OperationDefinition("ndvi", "NDVI", ("red", "nir"), {}),
}

SUPPORTED_CONNECTIONS = {
    ("aoi", "geometry", "dataset", "aoi"),
    ("aoi", "geometry", "operation", "aoi"),
    ("dataset", "raster", "operation", "raster"),
    ("operation", "raster", "visualization", "raster"),
}

VISUALIZATION_RAMPS = (
    {"id": "rdylgn", "label": "Red–yellow–green"},
    {"id": "viridis", "label": "Viridis"},
    {"id": "terrain", "label": "Terrain"},
    {"id": "grayscale", "label": "Grayscale"},
)


def serialize_definitions() -> dict[str, Any]:
    return {
        "node_types": [asdict(definition) for definition in NODE_DEFINITIONS.values()],
        "datasets": [asdict(definition) for definition in DATASET_DEFINITIONS.values()],
        "operations": [asdict(definition) for definition in OPERATION_DEFINITIONS.values()],
        "visualization_ramps": list(VISUALIZATION_RAMPS),
        "connections": [
            {
                "source_type": source_type,
                "source_port": source_port,
                "target_type": target_type,
                "target_port": target_port,
            }
            for source_type, source_port, target_type, target_port in sorted(SUPPORTED_CONNECTIONS)
        ],
    }
