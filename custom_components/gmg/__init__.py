"""The Green Mountain Grills integration."""
from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

from .api import GMGClient
from .const import DEFAULT_PORT, PLATFORMS
from .coordinator import GMGConfigEntry, GMGCoordinator
from .services import async_setup_services, async_unload_services

if TYPE_CHECKING:
    from homeassistant.helpers.typing import ConfigType


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register integration-wide services exactly once."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: GMGConfigEntry) -> bool:
    """Set up a GMG grill from a config entry."""
    client = GMGClient(
        host=entry.data[CONF_HOST],
        port=entry.data.get(CONF_PORT, DEFAULT_PORT),
    )
    coordinator = GMGCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GMGConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.client.async_close()
    if not hass.config_entries.async_loaded_entries(entry.domain):
        async_unload_services(hass)
    return unloaded


async def async_migrate_entry(hass: HomeAssistant, entry: GMGConfigEntry) -> bool:
    """Migrate an old config entry to the current schema."""
    return True
