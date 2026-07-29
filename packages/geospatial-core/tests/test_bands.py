import pytest

from geoflow_geospatial import (
    Band,
    SatelliteDataset,
    UnsupportedDatasetError,
    asset_name,
    band_mapping,
)


def test_satellite_band_mappings_use_provider_asset_names() -> None:
    sentinel = band_mapping(SatelliteDataset.SENTINEL_2_L2A)
    landsat_8 = band_mapping(SatelliteDataset.LANDSAT_8_L2)
    landsat_9 = band_mapping(SatelliteDataset.LANDSAT_9_L2)

    assert sentinel[Band.RED] == "B04"
    assert sentinel[Band.NIR] == "B08"
    assert landsat_8[Band.RED] == "SR_B4"
    assert landsat_8[Band.NIR] == "SR_B5"
    assert landsat_9 == landsat_8
    assert asset_name("sentinel-2-l2a", "swir1") == "B11"


def test_unknown_dataset_is_rejected() -> None:
    with pytest.raises(UnsupportedDatasetError, match="not supported"):
        band_mapping("unknown-satellite")
