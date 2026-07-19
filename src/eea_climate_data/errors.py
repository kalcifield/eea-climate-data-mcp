class ClimatePolicyError(Exception):
    """Base class for expected application errors."""


class UpstreamError(ClimatePolicyError):
    """The EEA service was unavailable or returned an invalid response."""


class UnsafeQueryError(ClimatePolicyError, ValueError):
    """A query failed local safety validation."""


class NotFoundError(ClimatePolicyError, ValueError):
    """A requested metadata object does not exist."""
