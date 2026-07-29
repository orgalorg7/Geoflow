from pathlib import Path

import numpy as np
import pytest
from rasterio.transform import from_origin

from geoflow_geospatial import Band, Raster, write_geotiff


@pytest.fixture
def deterministic_bands() -> dict[Band, Raster]:
    transform = from_origin(30.0, 31.0, 0.01, 0.01)
    mask = np.zeros((4, 4), dtype=bool)
    mask[3, 3] = True
    values = {
        Band.BLUE: np.array(
            [
                [1, 1, 1, 1],
                [2, 2, 2, 2],
                [3, 3, 3, 3],
                [4, 4, 4, 4],
            ],
            dtype=np.float32,
        ),
        Band.GREEN: np.array(
            [
                [2, 4, 6, 8],
                [1, 3, 5, 7],
                [4, 6, 8, 10],
                [2, 4, 6, 8],
            ],
            dtype=np.float32,
        ),
        Band.RED: np.array(
            [
                [1, 2, 3, 4],
                [1, 2, 3, 4],
                [2, 2, 2, 2],
                [4, 3, 2, 1],
            ],
            dtype=np.float32,
        ),
        Band.NIR: np.array(
            [
                [3, 2, -3, 8],
                [1, 4, 6, 2],
                [4, 4, 4, 4],
                [8, 6, 4, 2],
            ],
            dtype=np.float32,
        ),
        Band.SWIR1: np.array(
            [
                [4, 3, 2, 1],
                [2, 6, 8, 4],
                [8, 6, 4, 2],
                [10, 8, 6, 4],
            ],
            dtype=np.float32,
        ),
        Band.SWIR2: np.array(
            [
                [5, 4, 3, 2],
                [3, 7, 9, 5],
                [9, 7, 5, 3],
                [11, 9, 7, 5],
            ],
            dtype=np.float32,
        ),
    }
    return {
        band: Raster(
            data,
            transform=transform,
            crs="EPSG:4326",
            mask=mask,
            name=band.value,
        )
        for band, data in values.items()
    }


@pytest.fixture
def deterministic_raster_files(
    tmp_path: Path,
    deterministic_bands: dict[Band, Raster],
) -> dict[Band, Path]:
    paths: dict[Band, Path] = {}
    for band, raster in deterministic_bands.items():
        path = tmp_path / f"{band.value}.tif"
        write_geotiff(raster, path)
        paths[band] = path
    return paths
