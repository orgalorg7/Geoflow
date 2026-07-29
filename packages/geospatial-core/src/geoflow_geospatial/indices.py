from collections.abc import Mapping
from enum import StrEnum

import numpy as np

from geoflow_geospatial.bands import Band
from geoflow_geospatial.errors import RasterValidationError, UnsupportedIndexError
from geoflow_geospatial.raster import DEFAULT_NODATA, Raster, assert_aligned


class IndexType(StrEnum):
    NDVI = "ndvi"
    NDWI = "ndwi"
    NDBI = "ndbi"
    SAVI = "savi"


INDEX_BAND_REQUIREMENTS: dict[IndexType, tuple[Band, ...]] = {
    IndexType.NDVI: (Band.RED, Band.NIR),
    IndexType.NDWI: (Band.GREEN, Band.NIR),
    IndexType.NDBI: (Band.SWIR1, Band.NIR),
    IndexType.SAVI: (Band.RED, Band.NIR),
}


def required_bands(index: IndexType | str) -> tuple[Band, ...]:
    try:
        return INDEX_BAND_REQUIREMENTS[IndexType(index)]
    except ValueError as exc:
        raise UnsupportedIndexError(f"Index '{index}' is not supported") from exc


def calculate_index(
    index: IndexType | str,
    bands: Mapping[Band | str, Raster],
    *,
    savi_l: float = 0.5,
) -> Raster:
    try:
        operation = IndexType(index)
    except ValueError as exc:
        raise UnsupportedIndexError(f"Index '{index}' is not supported") from exc
    normalized = {Band(key): value for key, value in bands.items()}
    missing = set(required_bands(operation)) - set(normalized)
    if missing:
        names = ", ".join(sorted(band.value for band in missing))
        raise RasterValidationError(f"{operation.value.upper()} requires bands: {names}")

    if operation is IndexType.NDVI:
        return ndvi(normalized[Band.RED], normalized[Band.NIR])
    if operation is IndexType.NDWI:
        return ndwi(normalized[Band.GREEN], normalized[Band.NIR])
    if operation is IndexType.NDBI:
        return ndbi(normalized[Band.SWIR1], normalized[Band.NIR])
    return savi(
        normalized[Band.RED],
        normalized[Band.NIR],
        soil_adjustment=savi_l,
    )


def ndvi(red: Raster, nir: Raster) -> Raster:
    return _normalized_difference(nir, red, name=IndexType.NDVI.value)


def ndwi(green: Raster, nir: Raster) -> Raster:
    return _normalized_difference(green, nir, name=IndexType.NDWI.value)


def ndbi(swir1: Raster, nir: Raster) -> Raster:
    return _normalized_difference(swir1, nir, name=IndexType.NDBI.value)


def savi(
    red: Raster,
    nir: Raster,
    *,
    soil_adjustment: float = 0.5,
) -> Raster:
    if (
        isinstance(soil_adjustment, bool)
        or not isinstance(soil_adjustment, (int, float))
        or not 0 <= soil_adjustment <= 1
    ):
        raise RasterValidationError("SAVI soil adjustment factor must be between 0 and 1")
    assert_aligned(red, nir)
    denominator = nir.data + red.data + soil_adjustment
    mask = red.mask | nir.mask | np.isclose(denominator, 0)
    output = np.full(red.shape, DEFAULT_NODATA, dtype=np.float32)
    with np.errstate(divide="ignore", invalid="ignore"):
        np.divide(
            (1 + soil_adjustment) * (nir.data - red.data),
            denominator,
            out=output,
            where=~mask,
        )
    mask |= ~np.isfinite(output)
    return Raster(
        output,
        transform=red.transform,
        crs=red.crs,
        mask=mask,
        nodata=DEFAULT_NODATA,
        name=IndexType.SAVI.value,
    )


def _normalized_difference(first: Raster, second: Raster, *, name: str) -> Raster:
    assert_aligned(first, second)
    denominator = first.data + second.data
    mask = first.mask | second.mask | np.isclose(denominator, 0)
    output = np.full(first.shape, DEFAULT_NODATA, dtype=np.float32)
    with np.errstate(divide="ignore", invalid="ignore"):
        np.divide(
            first.data - second.data,
            denominator,
            out=output,
            where=~mask,
        )
    mask |= ~np.isfinite(output)
    return Raster(
        output,
        transform=first.transform,
        crs=first.crs,
        mask=mask,
        nodata=DEFAULT_NODATA,
        name=name,
    )
