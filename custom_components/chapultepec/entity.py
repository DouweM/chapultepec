"""Base entity for the Bosque de Chapultepec integration."""

from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import ChapultepecCoordinator


class ChapultepecEntity(CoordinatorEntity[ChapultepecCoordinator]):
    """Common base tying entities to the single park device."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: ChapultepecCoordinator, key: str) -> None:
        """Initialise the entity with a stable unique id."""
        super().__init__(coordinator)
        api_key = coordinator.client.api_key
        self._attr_unique_id = f"{api_key}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, api_key)},
            name="Bosque de Chapultepec",
            manufacturer="Fideicomiso Pro Bosque de Chapultepec",
            model="Attractions.io venue app",
            configuration_url="https://www.chapultepec.org.mx/",
        )
