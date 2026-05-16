"""Constants for the GMG integration."""
from __future__ import annotations

import logging

from homeassistant.const import Platform

DOMAIN = "gmg"
LOGGER = logging.getLogger(__package__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SENSOR,
]

DEFAULT_PORT = 8080
DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 600

CONF_SERIAL = "serial"
CONF_SCAN_INTERVAL = "scan_interval"

MANUFACTURER = "Green Mountain Grills"

MIN_GRILL_TEMP_F = 150
MAX_GRILL_TEMP_F = 550
GRILL_TEMP_STEP_F = 5
MIN_PROBE_TARGET_F = 32
MAX_PROBE_TARGET_F = 257
