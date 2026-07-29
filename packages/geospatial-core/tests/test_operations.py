import pytest

from geoflow_geospatial import (
    Band,
    GeometryOutsideRasterError,
    Raster,
    clip_raster,
    reproject_raster,
)


def test_clip_raster_crops_to_aoi(
    deterministic_bands: dict[Band, Raster],
) -> None:
    raster = deterministic_bands[Band.RED]
    aoi = {
        "type": "Polygon",
        "coordinates": [
            [
                [30.0101, 30.9701],
                [30.0299, 30.9701],
                [30.0299, 30.9899],
                [30.0101, 30.9899],
                [30.0101, 30.9701],
            ]
        ],
    }

    clipped = clip_raster(raster, aoi)

    assert clipped.shape == (2, 2)
    assert clipped.bounds == pytest.approx((30.01, 30.97, 30.03, 30.99))
    assert clipped.crs == raster.crs


def test_clip_rejects_non_overlapping_aoi(
    deterministic_bands: dict[Band, Raster],
) -> None:
    outside = {
        "type": "Polygon",
        "coordinates": [
            [
                [10.0, 10.0],
                [10.1, 10.0],
                [10.1, 10.1],
                [10.0, 10.1],
                [10.0, 10.0],
            ]
        ],
    }
    with pytest.raises(GeometryOutsideRasterError, match="does not overlap"):
        clip_raster(deterministic_bands[Band.RED], outside)


def test_reproject_changes_crs_and_preserves_valid_values(
    deterministic_bands: dict[Band, Raster],
) -> None:
    source = deterministic_bands[Band.RED]

    projected = reproject_raster(source, "EPSG:3857")

    assert projected.crs.to_epsg() == 3857
    assert projected.width > 0
    assert projected.height > 0
    assert projected.valid_data.size > 0
    assert projected.name == source.name


def test_raster_is_immutable_and_normalizes_non_finite_values(
    deterministic_bands: dict[Band, Raster],
) -> None:
    source = deterministic_bands[Band.RED]
    with pytest.raises(ValueError):
        source.data[0, 0] = 99

    values = source.data.copy()
    values[0, 0] = float("nan")
    normalized = Raster(
        values,
        transform=source.transform,
        crs=source.crs,
    )
    assert normalized.mask[0, 0]
