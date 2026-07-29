from pathlib import Path

from PIL import Image

from geoflow_geospatial import (
    Band,
    IndexType,
    build_index_artifacts,
    inspect_raster,
)


def test_full_local_ndvi_pipeline_creates_verified_artifacts(
    tmp_path: Path,
    deterministic_bands,
) -> None:
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
    geotiff_path = tmp_path / "analysis" / "ndvi.tif"
    preview_path = tmp_path / "analysis" / "ndvi.png"

    artifacts = build_index_artifacts(
        {
            Band.RED: deterministic_bands[Band.RED],
            Band.NIR: deterministic_bands[Band.NIR],
        },
        IndexType.NDVI,
        aoi=aoi,
        output_geotiff=geotiff_path,
        output_preview=preview_path,
        classify=True,
        preview_minimum=-1,
        preview_maximum=1,
    )

    assert artifacts.raster.shape == (2, 2)
    assert artifacts.statistics.valid_pixel_count == 4
    assert artifacts.classification is not None
    assert geotiff_path.exists()
    assert preview_path.exists()
    assert inspect_raster(geotiff_path).cloud_optimized
    with Image.open(preview_path) as preview:
        assert preview.size == (2, 2)
