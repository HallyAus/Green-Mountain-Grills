"""Base entity for the GMG integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import GMGCoordinator


class GMGBaseEntity(CoordinatorEntity[GMGCoordinator]):
    """Base class for all GMG entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: GMGCoordinator) -> None:
        """Initialize the entity and bind it to its parent device."""
        super().__init__(coordinator)
        serial = coordinator.info.serial
        model_id = coordinator.info.model_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            name=f"GMG {serial}",
            manufacturer=MANUFACTURER,
            model=coordinator.info.model,
            model_id=str(model_id) if model_id is not None else None,
            sw_version=coordinator.info.firmware,
            serial_number=serial,
            configuration_url=f"http://{coordinator.client.host}",
        )

    @property
    def available(self) -> bool:
        """Return True if the coordinator has produced at least one snapshot."""
        return super().available and self.coordinator.data is not None
