from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from geoflow_geospatial import (
    Band,
    IndexType,
    Raster,
    calculate_statistics,
    classify_index,
    inspect_raster,
    ndvi,
    read_raster,
    render_classification_preview,
    render_preview,
    write_cog,
)


def test_statistics_include_valid_and_nodata_counts(
    deterministic_bands: dict[Band, Raster],
) -> None:
    result = ndvi(deterministic_bands[Band.RED], deterministic_bands[Band.NIR])

    statistics = calculate_statistics(result)

    assert statistics.minimum == pytest.approx(-1 / 3)
    assert statistics.maximum == pytest.approx(0.5)
    assert statistics.mean is not None
    assert statistics.standard_deviation is not None
    assert statistics.valid_pixel_count == 14
    assert statistics.nodata_pixel_count == 2


def test_optional_classification_assigns_legend_codes(
    deterministic_bands: dict[Band, Raster],
) -> None:
    result = ndvi(deterministic_bands[Band.RED], deterministic_bands[Band.NIR])

    classified = classify_index(result, IndexType.NDVI)

    assert classified.classes.shape == result.shape
    assert classified.mask[0, 2]
    assert classified.classes[0, 0] == 4
    assert {rule.label for rule in classified.rules} >= {
        "Sparse vegetation",
        "Dense vegetation",
    }


def test_previews_do_not_change_analytical_values(
    tmp_path: Path,
    deterministic_bands: dict[Band, Raster],
) -> None:
    result = ndvi(deterministic_bands[Band.RED], deterministic_bands[Band.NIR])
    original_data = result.data.copy()
    original_mask = result.mask.copy()
    preview_path = tmp_path / "ndvi.png"
    classes_path = tmp_path / "ndvi-classes.png"

    render_preview(result, preview_path, minimum=-1, maximum=1)
    render_classification_preview(
        classify_index(result, IndexType.NDVI),
        classes_path,
    )

    assert np.array_equal(result.data, original_data)
    assert np.array_equal(result.mask, original_mask)
    with Image.open(preview_path) as preview:
        assert preview.mode == "RGBA"
        assert preview.size == (result.width, result.height)
        assert preview.getpixel((2, 0))[3] == 0
    with Image.open(classes_path) as preview:
        assert preview.mode == "RGBA"


def test_cog_round_trip_preserves_metadata_and_mask(
    tmp_path: Path,
    deterministic_bands: dict[Band, Raster],
) -> None:
    result = ndvi(deterministic_bands[Band.RED], deterministic_bands[Band.NIR])
    output = write_cog(result, tmp_path / "ndvi.tif", block_size=128)

    info = inspect_raster(output)
    reopened = read_raster(output)

    assert info.driver == "GTiff"
    assert info.cloud_optimized
    assert info.tiled
    assert info.crs == "EPSG:4326"
    assert reopened.shape == result.shape
    assert np.array_equal(reopened.mask, result.mask)
    assert np.allclose(reopened.valid_data, result.valid_data)


def test_generated_fixture_geotiffs_are_readable(
    deterministic_raster_files: dict[Band, Path],
) -> None:
    red = read_raster(deterministic_raster_files[Band.RED], name="red")

    assert red.name == "red"
    assert red.shape == (4, 4)
    assert red.crs.to_epsg() == 4326
    assert red.mask[3, 3]
