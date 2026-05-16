"""Sensor platform for the Green Mountain Grills integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .api import FireState, PowerState, WarnCode
from .coordinator import GMGConfigEntry, GMGCoordinator
from .entity import GMGBaseEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class GMGSensorDescription(SensorEntityDescription):
    """Describe a GMG sensor with a coordinator-bound value function."""

    value_fn: Callable[[GMGCoordinator], StateType]


SENSORS: tuple[GMGSensorDescription, ...] = (
    GMGSensorDescription(
        key="grill_temperature",
        translation_key="grill_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        suggested_display_precision=0,
        value_fn=lambda c: c.data.grill_temp,
    ),
    GMGSensorDescription(
        key="probe_1_temperature",
        translation_key="probe_1_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        suggested_display_precision=0,
        entity_registry_enabled_default=True,
        value_fn=lambda c: c.data.probe_1_temp,
    ),
    GMGSensorDescription(
        key="probe_2_temperature",
        translation_key="probe_2_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        suggested_display_precision=0,
        entity_registry_enabled_default=True,
        value_fn=lambda c: c.data.probe_2_temp,
    ),
    GMGSensorDescription(
        key="power_state",
        translation_key="power_state",
        device_class=SensorDeviceClass.ENUM,
        options=[member.name.lower() for member in PowerState],
        value_fn=lambda c: c.data.power_state.name.lower(),
    ),
    GMGSensorDescription(
        key="fire_state",
        translation_key="fire_state",
        device_class=SensorDeviceClass.ENUM,
        options=[member.name.lower() for member in FireState],
        value_fn=lambda c: c.data.fire_state.name.lower(),
    ),
    GMGSensorDescription(
        key="warning",
        translation_key="warning",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        options=[member.name.lower() for member in WarnCode],
        value_fn=lambda c: c.data.warn_code.name.lower(),
    ),
    GMGSensorDescription(
        key="hopper",
        translation_key="hopper",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        # Hopper level is a heuristic derived from auger runtime; disabled by default.
        entity_registry_enabled_default=False,
        value_fn=lambda c: c.data.hopper_pct,
    ),
    GMGSensorDescription(
        key="firmware_version",
        translation_key="firmware_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.info.firmware,
    ),
    GMGSensorDescription(
        key="model",
        translation_key="model",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda c: c.info.model,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GMGConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up GMG sensors from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        GMGSensor(coordinator, description) for description in SENSORS
    )


class GMGSensor(GMGBaseEntity, SensorEntity):
    """A single GMG sensor backed by a description."""

    entity_description: GMGSensorDescription

    def __init__(
        self,
        coordinator: GMGCoordinator,
        description: GMGSensorDescription,
    ) -> None:
        """Initialize the sensor entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.info.serial}_{description.key}"

    @property
    def native_value(self) -> StateType:
        """Return the value from the description's value function."""
        return self.entity_description.value_fn(self.coordinator)
