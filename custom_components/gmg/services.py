"""Service handlers for the Green Mountain Grills integration.

Register these from custom_components.gmg.__init__.async_setup() by calling
``async_setup_services(hass)``. ``async_unload_services(hass)`` is provided for
symmetry but is not normally required since HA tears services down on reload.
"""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .api import GMGInvalidValueError
from .const import (
    DOMAIN,
    LOGGER,
    MAX_PROBE_TARGET_F,
    MIN_PROBE_TARGET_F,
)
from .coordinator import GMGConfigEntry, GMGCoordinator

ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_PROBE = "probe"

SERVICE_SET_PROBE_TARGET = "set_probe_target"
SERVICE_REFRESH = "refresh"

_SET_PROBE_TARGET_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_PROBE): vol.All(vol.Coerce(int), vol.Range(min=1, max=2)),
        vol.Required(ATTR_TEMPERATURE): vol.All(
            vol.Coerce(int),
            vol.Range(min=MIN_PROBE_TARGET_F, max=MAX_PROBE_TARGET_F),
        ),
    }
)

_REFRESH_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
    }
)


def _resolve_coordinator(
    hass: HomeAssistant, entry_id: str
) -> GMGCoordinator:
    """Resolve a loaded GMG coordinator by config entry id."""
    entry: GMGConfigEntry | None = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="entry_not_found",
            translation_placeholders={"entry_id": entry_id},
        )
    if entry.state is not ConfigEntryState.LOADED:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="entry_not_loaded",
            translation_placeholders={"entry_id": entry_id},
        )
    return entry.runtime_data


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the GMG domain services."""

    async def _async_set_probe_target(call: ServiceCall) -> None:
        """Handle gmg.set_probe_target."""
        coordinator = _resolve_coordinator(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        probe = call.data[ATTR_PROBE]
        temperature = call.data[ATTR_TEMPERATURE]
        try:
            await coordinator.async_set_probe_target(probe, temperature)
        except ServiceValidationError:
            raise
        except GMGInvalidValueError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_value",
            ) from err
        except HomeAssistantError:
            raise
        except Exception as err:  # noqa: BLE001 - defensive service boundary
            LOGGER.exception("set_probe_target service failed")
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="service_call_failed",
            ) from err

    async def _async_refresh(call: ServiceCall) -> None:
        """Handle gmg.refresh."""
        coordinator = _resolve_coordinator(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PROBE_TARGET,
        _async_set_probe_target,
        schema=_SET_PROBE_TARGET_SCHEMA,
        supports_response=SupportsResponse.NONE,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH,
        _async_refresh,
        schema=_REFRESH_SCHEMA,
        supports_response=SupportsResponse.NONE,
    )


@callback
def async_unload_services(hass: HomeAssistant) -> None:
    """Remove the GMG domain services."""
    for service in (SERVICE_SET_PROBE_TARGET, SERVICE_REFRESH):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
