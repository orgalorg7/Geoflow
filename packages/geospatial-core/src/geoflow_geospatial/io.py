from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio

from geoflow_geospatial.errors import RasterValidationError
from geoflow_geospatial.raster import DEFAULT_NODATA, Raster


@dataclass(frozen=True)
class RasterFileInfo:
    path: Path
    driver: str
    crs: str
    width: int
    height: int
    dtype: str
    nodata: float | None
    tiled: bool
    cloud_optimized: bool


def read_raster(path: str | Path, *, band: int = 1, name: str | None = None) -> Raster:
    source_path = Path(path)
    with rasterio.open(source_path) as dataset:
        if not 1 <= band <= dataset.count:
            raise RasterValidationError(f"Raster band must be between 1 and {dataset.count}")
        if dataset.crs is None:
            raise RasterValidationError("Raster file does not define a CRS")
        values = dataset.read(band).astype(np.float32)
        invalid = dataset.read_masks(band) == 0
        nodata = (
            float(dataset.nodata)
            if dataset.nodata is not None and np.isfinite(dataset.nodata)
            else DEFAULT_NODATA
        )
        invalid |= ~np.isfinite(values)
        if dataset.nodata is not None:
            invalid |= np.isclose(values, dataset.nodata)
        return Raster(
            values,
            transform=dataset.transform,
            crs=dataset.crs,
            mask=invalid,
            nodata=nodata,
            name=name or source_path.stem,
        )


def write_geotiff(raster: Raster, path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        output_path,
        "w",
        driver="GTiff",
        height=raster.height,
        width=raster.width,
        count=1,
        dtype="float32",
        crs=raster.crs,
        transform=raster.transform,
        nodata=raster.nodata,
        compress="deflate",
    ) as dataset:
        dataset.write(raster.filled(), 1)
        dataset.write_mask((~raster.mask).astype(np.uint8) * 255)
    return output_path


def write_cog(
    raster: Raster,
    path: str | Path,
    *,
    compression: str = "DEFLATE",
    block_size: int = 512,
) -> Path:
    """Write a Cloud Optimized GeoTIFF through GDAL's COG driver."""

    if block_size < 128 or block_size > 4096 or block_size % 16:
        raise RasterValidationError("COG block size must be a multiple of 16 between 128 and 4096")
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        output_path,
        "w",
        driver="COG",
        height=raster.height,
        width=raster.width,
        count=1,
        dtype="float32",
        crs=raster.crs,
        transform=raster.transform,
        nodata=raster.nodata,
        compress=compression,
        blocksize=block_size,
        overview_resampling="average",
    ) as dataset:
        dataset.write(raster.filled(), 1)
        dataset.write_mask((~raster.mask).astype(np.uint8) * 255)
    return output_path


def inspect_raster(path: str | Path) -> RasterFileInfo:
    source_path = Path(path)
    with rasterio.open(source_path) as dataset:
        image_structure = dataset.tags(ns="IMAGE_STRUCTURE")
        cloud_optimized = image_structure.get("LAYOUT") == "COG"
        return RasterFileInfo(
            path=source_path,
            driver=dataset.driver,
            crs=dataset.crs.to_string() if dataset.crs else "",
            width=dataset.width,
            height=dataset.height,
            dtype=dataset.dtypes[0],
            nodata=dataset.nodata,
            tiled=cloud_optimized
            or any(
                block_height < dataset.height or block_width < dataset.width
                for block_height, block_width in dataset.block_shapes
            ),
            cloud_optimized=cloud_optimized,
        )
