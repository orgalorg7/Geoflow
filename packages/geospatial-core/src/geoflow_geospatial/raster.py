from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from affine import Affine
from numpy.typing import NDArray
from rasterio.crs import CRS
from rasterio.transform import array_bounds

from geoflow_geospatial.errors import RasterAlignmentError, RasterValidationError

DEFAULT_NODATA = -9999.0


@dataclass(frozen=True)
class Raster:
    """A single immutable, georeferenced analytical raster band."""

    data: NDArray[np.floating[Any]]
    transform: Affine
    crs: CRS | str
    mask: NDArray[np.bool_] | None = None
    nodata: float = DEFAULT_NODATA
    name: str | None = None

    def __post_init__(self) -> None:
        data = np.asarray(self.data, dtype=np.float32).copy()
        if data.ndim != 2 or data.size == 0:
            raise RasterValidationError("Raster data must be a non-empty 2D array")
        try:
            crs = CRS.from_user_input(self.crs)
        except (TypeError, ValueError) as exc:
            raise RasterValidationError("Raster CRS is invalid") from exc
        if not isinstance(self.transform, Affine):
            raise RasterValidationError("Raster transform must be an Affine transform")
        if not np.isfinite(self.nodata):
            raise RasterValidationError("Raster NoData value must be finite")

        if self.mask is None:
            mask = np.zeros(data.shape, dtype=bool)
        else:
            mask = np.asarray(self.mask, dtype=bool).copy()
            if mask.shape != data.shape:
                raise RasterValidationError("Raster mask must match the data shape")
        mask |= ~np.isfinite(data)
        data[mask] = self.nodata
        data.setflags(write=False)
        mask.setflags(write=False)
        object.__setattr__(self, "data", data)
        object.__setattr__(self, "mask", mask)
        object.__setattr__(self, "crs", crs)

    @property
    def height(self) -> int:
        return int(self.data.shape[0])

    @property
    def width(self) -> int:
        return int(self.data.shape[1])

    @property
    def shape(self) -> tuple[int, int]:
        return self.data.shape

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        return array_bounds(self.height, self.width, self.transform)

    @property
    def valid_data(self) -> NDArray[np.float32]:
        return self.data[~self.mask]

    def filled(self) -> NDArray[np.float32]:
        values = self.data.copy()
        values[self.mask] = self.nodata
        return values


def assert_aligned(reference: Raster, *others: Raster) -> None:
    """Require all bands to share shape, CRS, and pixel transform."""

    for raster in others:
        if raster.shape != reference.shape:
            raise RasterAlignmentError("Raster bands must have the same dimensions")
        if raster.crs != reference.crs:
            raise RasterAlignmentError("Raster bands must use the same CRS")
        if not raster.transform.almost_equals(reference.transform):
            raise RasterAlignmentError("Raster bands must use the same pixel grid")
