class HunClimateError(Exception):
    """Base class for expected application errors."""


class UpstreamError(HunClimateError):
    """The EEA service was unavailable or returned an invalid response."""


class UnsafeQueryError(HunClimateError, ValueError):
    """A query failed local safety validation."""


class NotFoundError(HunClimateError, ValueError):
    """A requested metadata object does not exist."""
