from dataclasses import dataclass
from enum import StrEnum

from geoflow_geospatial.errors import UnsupportedDatasetError
from geoflow_geospatial.raster import Raster


class Band(StrEnum):
    BLUE = "blue"
    GREEN = "green"
    RED = "red"
    NIR = "nir"
    SWIR1 = "swir1"
    SWIR2 = "swir2"


class SatelliteDataset(StrEnum):
    SENTINEL_2_L2A = "sentinel-2-l2a"
    LANDSAT_8_L2 = "landsat-8-l2"
    LANDSAT_9_L2 = "landsat-9-l2"


@dataclass(frozen=True)
class RasterBand:
    logical_band: Band
    raster: Raster
    asset_name: str | None = None


DATASET_BAND_MAPPINGS: dict[SatelliteDataset, dict[Band, str]] = {
    SatelliteDataset.SENTINEL_2_L2A: {
        Band.BLUE: "B02",
        Band.GREEN: "B03",
        Band.RED: "B04",
        Band.NIR: "B08",
        Band.SWIR1: "B11",
        Band.SWIR2: "B12",
    },
    SatelliteDataset.LANDSAT_8_L2: {
        Band.BLUE: "SR_B2",
        Band.GREEN: "SR_B3",
        Band.RED: "SR_B4",
        Band.NIR: "SR_B5",
        Band.SWIR1: "SR_B6",
        Band.SWIR2: "SR_B7",
    },
    SatelliteDataset.LANDSAT_9_L2: {
        Band.BLUE: "SR_B2",
        Band.GREEN: "SR_B3",
        Band.RED: "SR_B4",
        Band.NIR: "SR_B5",
        Band.SWIR1: "SR_B6",
        Band.SWIR2: "SR_B7",
    },
}


def band_mapping(dataset: SatelliteDataset | str) -> dict[Band, str]:
    try:
        dataset_id = SatelliteDataset(dataset)
    except ValueError as exc:
        raise UnsupportedDatasetError(f"Dataset '{dataset}' is not supported") from exc
    return dict(DATASET_BAND_MAPPINGS[dataset_id])


def asset_name(dataset: SatelliteDataset | str, band: Band | str) -> str:
    mapping = band_mapping(dataset)
    try:
        logical_band = Band(band)
    except ValueError as exc:
        raise UnsupportedDatasetError(f"Logical band '{band}' is not supported") from exc
    return mapping[logical_band]
