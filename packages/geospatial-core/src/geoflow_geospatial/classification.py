from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from geoflow_geospatial.errors import RasterValidationError
from geoflow_geospatial.indices import IndexType
from geoflow_geospatial.raster import Raster

RGBColor = tuple[int, int, int]


@dataclass(frozen=True)
class IndexClass:
    code: int
    label: str
    minimum: float
    maximum: float
    color: RGBColor


@dataclass(frozen=True)
class ClassifiedRaster:
    classes: NDArray[np.uint8]
    mask: NDArray[np.bool_]
    rules: tuple[IndexClass, ...]

    def __post_init__(self) -> None:
        classes = np.asarray(self.classes, dtype=np.uint8).copy()
        mask = np.asarray(self.mask, dtype=bool).copy()
        if classes.ndim != 2 or classes.shape != mask.shape:
            raise RasterValidationError("Classification and mask dimensions must match")
        classes[mask] = 0
        classes.setflags(write=False)
        mask.setflags(write=False)
        object.__setattr__(self, "classes", classes)
        object.__setattr__(self, "mask", mask)


DEFAULT_INDEX_CLASSES: dict[IndexType, tuple[IndexClass, ...]] = {
    IndexType.NDVI: (
        IndexClass(1, "Water or non-vegetated", -1.0, 0.0, (165, 38, 38)),
        IndexClass(2, "Sparse vegetation", 0.0, 0.2, (244, 177, 70)),
        IndexClass(3, "Moderate vegetation", 0.2, 0.5, (173, 214, 92)),
        IndexClass(4, "Dense vegetation", 0.5, 1.000001, (26, 122, 64)),
    ),
    IndexType.NDWI: (
        IndexClass(1, "Dry surface", -1.0, 0.0, (166, 97, 26)),
        IndexClass(2, "Moist surface", 0.0, 0.3, (103, 169, 207)),
        IndexClass(3, "Open water", 0.3, 1.000001, (8, 81, 156)),
    ),
    IndexType.NDBI: (
        IndexClass(1, "Vegetation or water", -1.0, 0.0, (92, 166, 77)),
        IndexClass(2, "Mixed surface", 0.0, 0.2, (238, 204, 120)),
        IndexClass(3, "Built-up surface", 0.2, 1.000001, (174, 55, 55)),
    ),
    IndexType.SAVI: (
        IndexClass(1, "Low vegetation", -1.0, 0.2, (190, 85, 52)),
        IndexClass(2, "Moderate vegetation", 0.2, 0.5, (173, 214, 92)),
        IndexClass(3, "Dense vegetation", 0.5, 1.500001, (26, 122, 64)),
    ),
}


def classify_index(
    raster: Raster,
    index: IndexType | str,
    *,
    rules: tuple[IndexClass, ...] | None = None,
) -> ClassifiedRaster:
    selected_rules = rules or DEFAULT_INDEX_CLASSES[IndexType(index)]
    _validate_rules(selected_rules)
    classes = np.zeros(raster.shape, dtype=np.uint8)
    for rule in selected_rules:
        matches = ~raster.mask & (raster.data >= rule.minimum) & (raster.data < rule.maximum)
        classes[matches] = rule.code
    mask = raster.mask | (classes == 0)
    return ClassifiedRaster(classes=classes, mask=mask, rules=selected_rules)


def _validate_rules(rules: tuple[IndexClass, ...]) -> None:
    if not rules:
        raise RasterValidationError("At least one classification rule is required")
    codes: set[int] = set()
    for rule in rules:
        if not 1 <= rule.code <= 255 or rule.code in codes:
            raise RasterValidationError("Classification codes must be unique values from 1 to 255")
        if rule.minimum >= rule.maximum:
            raise RasterValidationError("Classification minimum must be below maximum")
        if len(rule.color) != 3 or any(not 0 <= channel <= 255 for channel in rule.color):
            raise RasterValidationError("Classification colors must contain valid RGB values")
        codes.add(rule.code)
