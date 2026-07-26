"""Binary sensors for Bosque de Chapultepec."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ChapultepecConfigEntry, ChapultepecCoordinator
from .entity import ChapultepecEntity


async def async_setup_entry(
    hass,
    entry: ChapultepecConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the park-open binary sensor."""
    async_add_entities([ParkOpenBinarySensor(entry.runtime_data)])


class ParkOpenBinarySensor(ChapultepecEntity, BinarySensorEntity):
    """Whether the park is currently open per today's published hours."""

    _attr_translation_key = "park_open"
    _attr_icon = "mdi:tree"

    def __init__(self, coordinator: ChapultepecCoordinator) -> None:
        """Initialise the park-open sensor."""
        super().__init__(coordinator, "park_open")

    @property
    def is_on(self) -> bool | None:
        """Return True when the park is open."""
        return self.coordinator.is_park_open()

    @property
    def available(self) -> bool:
        """Available only when today's hours are known."""
        return super().available and self.coordinator.resort_hours_today() is not None
