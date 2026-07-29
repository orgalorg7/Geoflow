from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from geoflow_geospatial.bands import Band
from geoflow_geospatial.classification import ClassifiedRaster, classify_index
from geoflow_geospatial.indices import IndexType, calculate_index
from geoflow_geospatial.io import write_cog
from geoflow_geospatial.operations import clip_raster
from geoflow_geospatial.preview import render_preview
from geoflow_geospatial.raster import Raster
from geoflow_geospatial.statistics import RasterStatistics, calculate_statistics


@dataclass(frozen=True)
class AnalysisArtifacts:
    raster: Raster
    statistics: RasterStatistics
    geotiff_path: Path
    preview_path: Path
    classification: ClassifiedRaster | None


def build_index_artifacts(
    bands: Mapping[Band | str, Raster],
    index: IndexType | str,
    *,
    output_geotiff: str | Path,
    output_preview: str | Path,
    aoi: dict[str, Any] | None = None,
    aoi_crs: str = "EPSG:4326",
    savi_l: float = 0.5,
    classify: bool = False,
    color_ramp: str = "rdylgn",
    preview_minimum: float | None = None,
    preview_maximum: float | None = None,
) -> AnalysisArtifacts:
    operation = IndexType(index)
    result = calculate_index(operation, bands, savi_l=savi_l)
    if aoi is not None:
        result = clip_raster(result, aoi, geometry_crs=aoi_crs)
    statistics = calculate_statistics(result)
    classification = classify_index(result, operation) if classify else None
    geotiff_path = write_cog(result, output_geotiff)
    preview_path = render_preview(
        result,
        output_preview,
        color_ramp=color_ramp,
        minimum=preview_minimum,
        maximum=preview_maximum,
    )
    return AnalysisArtifacts(
        raster=result,
        statistics=statistics,
        geotiff_path=geotiff_path,
        preview_path=preview_path,
        classification=classification,
    )
