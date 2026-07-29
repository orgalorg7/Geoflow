from pathlib import Path

import numpy as np
from PIL import Image

from geoflow_geospatial.classification import ClassifiedRaster
from geoflow_geospatial.errors import RasterValidationError
from geoflow_geospatial.raster import Raster
from geoflow_geospatial.statistics import calculate_statistics

ColorStop = tuple[float, tuple[int, int, int]]

COLOR_RAMPS: dict[str, tuple[ColorStop, ...]] = {
    "rdylgn": (
        (0.0, (165, 0, 38)),
        (0.5, (255, 255, 191)),
        (1.0, (0, 104, 55)),
    ),
    "viridis": (
        (0.0, (68, 1, 84)),
        (0.33, (49, 104, 142)),
        (0.66, (53, 183, 121)),
        (1.0, (253, 231, 37)),
    ),
    "terrain": (
        (0.0, (35, 98, 47)),
        (0.5, (190, 176, 112)),
        (0.8, (130, 105, 83)),
        (1.0, (255, 255, 255)),
    ),
    "grayscale": (
        (0.0, (0, 0, 0)),
        (1.0, (255, 255, 255)),
    ),
}


def render_preview(
    raster: Raster,
    output_path: str | Path,
    *,
    color_ramp: str = "rdylgn",
    minimum: float | None = None,
    maximum: float | None = None,
) -> Path:
    """Render a transparent RGBA PNG without modifying analytical values."""

    if color_ramp not in COLOR_RAMPS:
        raise RasterValidationError(f"Color ramp '{color_ramp}' is not supported")
    statistics = calculate_statistics(raster)
    lower = statistics.minimum if minimum is None else minimum
    upper = statistics.maximum if maximum is None else maximum
    if lower is None or upper is None:
        raise RasterValidationError("Cannot preview a raster with no valid pixels")
    if not np.isfinite(lower) or not np.isfinite(upper) or lower >= upper:
        raise RasterValidationError("Preview minimum must be lower than maximum")

    normalized = np.clip((raster.data.astype(np.float64) - lower) / (upper - lower), 0, 1)
    rgba = np.zeros((*raster.shape, 4), dtype=np.uint8)
    stops = COLOR_RAMPS[color_ramp]
    positions = np.array([stop[0] for stop in stops], dtype=np.float64)
    colors = np.array([stop[1] for stop in stops], dtype=np.float64)
    for channel in range(3):
        rgba[..., channel] = np.interp(
            normalized,
            positions,
            colors[:, channel],
        ).astype(np.uint8)
    rgba[..., 3] = np.where(raster.mask, 0, 255).astype(np.uint8)
    return _save_rgba(rgba, output_path)


def render_classification_preview(
    classification: ClassifiedRaster,
    output_path: str | Path,
) -> Path:
    rgba = np.zeros((*classification.classes.shape, 4), dtype=np.uint8)
    for rule in classification.rules:
        matches = (~classification.mask) & (classification.classes == rule.code)
        rgba[matches, :3] = rule.color
    rgba[..., 3] = np.where(classification.mask, 0, 255).astype(np.uint8)
    return _save_rgba(rgba, output_path)


def _save_rgba(rgba: np.ndarray, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, mode="RGBA").save(path, format="PNG")
    return path
