class GeospatialError(ValueError):
    """Base error for invalid geospatial operations."""


class RasterValidationError(GeospatialError):
    """Raised when raster data or metadata is invalid."""


class RasterAlignmentError(GeospatialError):
    """Raised when input bands are not on the same pixel grid."""


class GeometryOutsideRasterError(GeospatialError):
    """Raised when an AOI does not overlap a raster."""


class UnsupportedDatasetError(GeospatialError):
    """Raised when a dataset has no logical band mapping."""


class UnsupportedIndexError(GeospatialError):
    """Raised when an index operation is not implemented."""
