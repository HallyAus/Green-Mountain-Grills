"""Diagnostics support for the GMG integration."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .coordinator import GMGConfigEntry

TO_REDACT = {"host", "serial", "mac"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: GMGConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a GMG config entry."""
    coord = entry.runtime_data
    snap_dict: dict[str, Any] = asdict(coord.data) if coord.data else {}
    snap_dict.pop("raw", None)
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "grill": {
            "model": coord.info.model,
            "model_id": coord.info.model_id,
            "firmware": coord.info.firmware,
        },
        "snapshot": snap_dict,
    }
