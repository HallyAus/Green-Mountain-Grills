"""Climate platform for the Green Mountain Grills integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import FireState, PowerState
from .const import (
    GRILL_TEMP_STEP_F,
    LOGGER,
    MAX_GRILL_TEMP_F,
    MIN_GRILL_TEMP_F,
)
from .coordinator import GMGConfigEntry, GMGCoordinator
from .entity import GMGBaseEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GMGConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the grill climate entity from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities([GMGGrillClimate(coordinator)])


class GMGGrillClimate(GMGBaseEntity, ClimateEntity):
    """Climate entity controlling the whole grill."""

    _attr_name = None
    _attr_translation_key = "grill"
    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_target_temperature_step = GRILL_TEMP_STEP_F
    _attr_min_temp = MIN_GRILL_TEMP_F
    _attr_max_temp = MAX_GRILL_TEMP_F
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.FAN_ONLY]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: GMGCoordinator) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.info.serial}_climate"

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode derived from the snapshot."""
        snapshot = self.coordinator.data
        if snapshot.cold_smoke or snapshot.power_state is PowerState.COLD_SMOKE:
            return HVACMode.FAN_ONLY
        if snapshot.power_state is PowerState.OFF:
            return HVACMode.OFF
        return HVACMode.HEAT

    @property
    def hvac_action(self) -> HVACAction:
        """Return the current activity state."""
        snapshot = self.coordinator.data
        fire = snapshot.fire_state
        if fire is FireState.RUNNING:
            return HVACAction.HEATING
        # Cold smoke and fan-only run the fan without producing heat.
        if snapshot.power_state in (PowerState.FAN, PowerState.COLD_SMOKE):
            return HVACAction.IDLE
        if fire in (FireState.STARTUP, FireState.COOL_DOWN):
            return HVACAction.IDLE
        return HVACAction.OFF

    @property
    def current_temperature(self) -> float | None:
        """Return the grill probe temperature."""
        return self.coordinator.data.grill_temp

    @property
    def target_temperature(self) -> float | None:
        """Return the configured setpoint."""
        return self.coordinator.data.grill_set_temp

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set a new target temperature, snapped to the 5 degF grid."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        snapped = int(round(float(temperature) / GRILL_TEMP_STEP_F) * GRILL_TEMP_STEP_F)
        try:
            await self.coordinator.async_set_grill_temp(snapped)
        except HomeAssistantError:
            raise
        except Exception as err:  # noqa: BLE001 - defensive boundary
            LOGGER.exception("Unexpected error setting grill temperature")
            raise HomeAssistantError(str(err)) from err

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Switch between off, heat, and cold-smoke."""
        try:
            if hvac_mode is HVACMode.OFF:
                await self.coordinator.async_power_off()
            elif hvac_mode is HVACMode.HEAT:
                await self.coordinator.async_power_on()
            elif hvac_mode is HVACMode.FAN_ONLY:
                await self.coordinator.async_cold_smoke()
        except HomeAssistantError:
            raise

    async def async_turn_on(self) -> None:
        """Power the grill on."""
        await self.coordinator.async_power_on()

    async def async_turn_off(self) -> None:
        """Power the grill off."""
        await self.coordinator.async_power_off()
