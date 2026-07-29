import numpy as np
import pytest
from rasterio.transform import from_origin

from geoflow_geospatial import (
    Band,
    IndexType,
    Raster,
    RasterAlignmentError,
    RasterValidationError,
    calculate_index,
    ndbi,
    ndvi,
    ndwi,
    required_bands,
    savi,
)


def test_index_band_requirements_are_explicit() -> None:
    assert required_bands(IndexType.NDVI) == (Band.RED, Band.NIR)
    assert required_bands(IndexType.NDWI) == (Band.GREEN, Band.NIR)
    assert required_bands(IndexType.NDBI) == (Band.SWIR1, Band.NIR)
    assert required_bands(IndexType.SAVI) == (Band.RED, Band.NIR)


def test_ndvi_preserves_nodata_and_masks_division_by_zero(
    deterministic_bands: dict[Band, Raster],
) -> None:
    result = ndvi(deterministic_bands[Band.RED], deterministic_bands[Band.NIR])

    assert result.name == "ndvi"
    assert result.data[0, 0] == pytest.approx(0.5)
    assert result.data[0, 1] == pytest.approx(0)
    assert result.mask[0, 2]
    assert result.mask[3, 3]
    assert np.isfinite(result.valid_data).all()


def test_all_index_formulas_return_expected_values(
    deterministic_bands: dict[Band, Raster],
) -> None:
    ndwi_result = ndwi(
        deterministic_bands[Band.GREEN],
        deterministic_bands[Band.NIR],
    )
    ndbi_result = ndbi(
        deterministic_bands[Band.SWIR1],
        deterministic_bands[Band.NIR],
    )
    savi_result = savi(
        deterministic_bands[Band.RED],
        deterministic_bands[Band.NIR],
        soil_adjustment=0.5,
    )

    assert ndwi_result.data[0, 0] == pytest.approx(-0.2)
    assert ndbi_result.data[0, 0] == pytest.approx(1 / 7)
    assert savi_result.data[0, 0] == pytest.approx(2 / 3)
    assert not savi_result.mask[0, 2]


def test_calculate_index_dispatches_and_validates_inputs(
    deterministic_bands: dict[Band, Raster],
) -> None:
    result = calculate_index(
        "ndvi",
        {
            "red": deterministic_bands[Band.RED],
            "nir": deterministic_bands[Band.NIR],
        },
    )
    assert result.name == "ndvi"

    with pytest.raises(RasterValidationError, match="requires bands"):
        calculate_index("ndvi", {Band.RED: deterministic_bands[Band.RED]})
    with pytest.raises(RasterValidationError, match="between 0 and 1"):
        savi(
            deterministic_bands[Band.RED],
            deterministic_bands[Band.NIR],
            soil_adjustment=2,
        )


def test_misaligned_bands_are_rejected(
    deterministic_bands: dict[Band, Raster],
) -> None:
    shifted = Raster(
        deterministic_bands[Band.NIR].data,
        transform=from_origin(30.1, 31.0, 0.01, 0.01),
        crs="EPSG:4326",
    )

    with pytest.raises(RasterAlignmentError, match="pixel grid"):
        ndvi(deterministic_bands[Band.RED], shifted)
