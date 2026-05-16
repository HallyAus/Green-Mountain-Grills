"""Constants for the Green Mountain Grills async UDP protocol library."""

from __future__ import annotations

from typing import Final

DEFAULT_PORT: Final[int] = 8080
DEFAULT_BROADCAST: Final[str] = "255.255.255.255"

DEFAULT_REQUEST_TIMEOUT: Final[float] = 1.0
DEFAULT_MAX_RETRIES: Final[int] = 5
DEFAULT_DISCOVERY_TIMEOUT: Final[float] = 2.0

CMD_STATUS: Final[bytes] = b"UR001!"
CMD_SERIAL: Final[bytes] = b"UL!"
CMD_FIRMWARE: Final[bytes] = b"UN!"
CMD_POWER_ON: Final[bytes] = b"UK001!"
CMD_COLD_SMOKE: Final[bytes] = b"UK002!"
CMD_POWER_OFF: Final[bytes] = b"UK004!"

STATUS_FRAME_LEN: Final[int] = 36
STATUS_HEADER: Final[bytes] = b"UR"

PROBE_UNPLUGGED_SENTINEL: Final[int] = 89
LOW_PELLET_ALT_VALUE: Final[int] = 128

GRILL_TEMP_MIN: Final[int] = 150
GRILL_TEMP_MAX: Final[int] = 550
PROBE_TEMP_MIN: Final[int] = 32
PROBE_TEMP_MAX: Final[int] = 257

SERIAL_PREFIX: Final[bytes] = b"GMG"
