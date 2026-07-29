from dataclasses import dataclass

import numpy as np

from geoflow_geospatial.raster import Raster


@dataclass(frozen=True)
class RasterStatistics:
    minimum: float | None
    maximum: float | None
    mean: float | None
    standard_deviation: float | None
    valid_pixel_count: int
    nodata_pixel_count: int


def calculate_statistics(raster: Raster) -> RasterStatistics:
    values = raster.valid_data.astype(np.float64)
    valid_count = int(values.size)
    nodata_count = int(raster.data.size - valid_count)
    if valid_count == 0:
        return RasterStatistics(
            minimum=None,
            maximum=None,
            mean=None,
            standard_deviation=None,
            valid_pixel_count=0,
            nodata_pixel_count=nodata_count,
        )
    return RasterStatistics(
        minimum=float(np.min(values)),
        maximum=float(np.max(values)),
        mean=float(np.mean(values)),
        standard_deviation=float(np.std(values)),
        valid_pixel_count=valid_count,
        nodata_pixel_count=nodata_count,
    )
