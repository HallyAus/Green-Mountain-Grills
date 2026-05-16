"""Number platform for the Green Mountain Grills integration."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    GRILL_TEMP_STEP_F,
    LOGGER,
    MAX_GRILL_TEMP_F,
    MAX_PROBE_TARGET_F,
    MIN_GRILL_TEMP_F,
    MIN_PROBE_TARGET_F,
)
from .coordinator import GMGConfigEntry, GMGCoordinator
from .entity import GMGBaseEntity

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class GMGNumberDescription(NumberEntityDescription):
    """Describe a GMG number entity with bound read/write callbacks."""

    value_fn: Callable[[GMGCoordinator], int]
    set_fn: Callable[[GMGCoordinator, int], Awaitable[None]]


NUMBERS: tuple[GMGNumberDescription, ...] = (
    GMGNumberDescription(
        key="grill_setpoint",
        translation_key="grill_setpoint",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        native_min_value=MIN_GRILL_TEMP_F,
        native_max_value=MAX_GRILL_TEMP_F,
        native_step=GRILL_TEMP_STEP_F,
        mode=NumberMode.BOX,
        value_fn=lambda c: c.data.grill_set_temp,
        set_fn=lambda c, v: c.async_set_grill_temp(v),
    ),
    GMGNumberDescription(
        key="probe_1_target",
        translation_key="probe_1_target",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        native_min_value=MIN_PROBE_TARGET_F,
        native_max_value=MAX_PROBE_TARGET_F,
        native_step=1,
        mode=NumberMode.BOX,
        value_fn=lambda c: c.data.probe_1_target,
        set_fn=lambda c, v: c.async_set_probe_target(1, v),
    ),
    GMGNumberDescription(
        key="probe_2_target",
        translation_key="probe_2_target",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        native_min_value=MIN_PROBE_TARGET_F,
        native_max_value=MAX_PROBE_TARGET_F,
        native_step=1,
        mode=NumberMode.BOX,
        value_fn=lambda c: c.data.probe_2_target,
        set_fn=lambda c, v: c.async_set_probe_target(2, v),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GMGConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up GMG number entities from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        GMGNumber(coordinator, description) for description in NUMBERS
    )


class GMGNumber(GMGBaseEntity, NumberEntity):
    """A single GMG number entity backed by a description."""

    entity_description: GMGNumberDescription

    def __init__(
        self,
        coordinator: GMGCoordinator,
        description: GMGNumberDescription,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.info.serial}_{description.key}"

    @property
    def native_value(self) -> float | None:
        """Return the current value from the description."""
        return self.entity_description.value_fn(self.coordinator)

    async def async_set_native_value(self, value: float) -> None:
        """Push a new value to the grill via the description's set function."""
        try:
            await self.entity_description.set_fn(self.coordinator, int(value))
        except HomeAssistantError:
            raise
        except Exception as err:  # noqa: BLE001 - defensive boundary
            LOGGER.exception("Unexpected error setting %s", self.entity_description.key)
            raise HomeAssistantError(str(err)) from err
