"""Exception hierarchy for the Green Mountain Grills async UDP protocol library."""

from __future__ import annotations


class GMGError(Exception):
    """Base class for all GMG protocol errors."""


class GMGConnectionError(GMGError):
    """Socket-level failure or unreachable host."""


class GMGTimeoutError(GMGConnectionError):
    """No reply received within the configured retry budget."""


class GMGServerModeError(GMGConnectionError):
    """Retries exhausted to a reachable grill; controller likely in Server Mode."""


class GMGProtocolError(GMGError):
    """Malformed frame, wrong header, or truncated response."""


class GMGInvalidValueError(GMGError, ValueError):
    """Out-of-range or otherwise invalid setpoint argument."""
