"""Sensors for Bosque de Chapultepec."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .coordinator import ChapultepecConfigEntry, ChapultepecCoordinator
from .entity import ChapultepecEntity


@dataclass(frozen=True, kw_only=True)
class ChapultepecSensorDescription(SensorEntityDescription):
    """Describes a Chapultepec sensor."""

    value_fn: Callable[[ChapultepecCoordinator], StateType | datetime]
    attributes_fn: Callable[[ChapultepecCoordinator], dict[str, Any]] | None = None


def _opens_at(coordinator: ChapultepecCoordinator) -> datetime | None:
    hours = coordinator.resort_hours_today()
    return hours[0] if hours else None


def _closes_at(coordinator: ChapultepecCoordinator) -> datetime | None:
    hours = coordinator.resort_hours_today()
    return hours[1] if hours else None


def _events_today(coordinator: ChapultepecCoordinator) -> int:
    now = datetime.now(coordinator.tz)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return len(coordinator.events(start, start + timedelta(days=1)))


def _next_event_value(coordinator: ChapultepecCoordinator) -> str | None:
    event = coordinator.next_event()
    return event.poi.name if event else None


def _next_event_attrs(coordinator: ChapultepecCoordinator) -> dict[str, Any]:
    event = coordinator.next_event()
    if event is None:
        return {}
    attrs: dict[str, Any] = {
        "start": event.start.isoformat(),
        "end": None if event.is_instant else event.end.isoformat(),
        "categories": [c.name for c in event.categories if c.name],
    }
    if event.poi.location:
        attrs["latitude"], attrs["longitude"] = event.poi.location
    return attrs


SENSORS: tuple[ChapultepecSensorDescription, ...] = (
    ChapultepecSensorDescription(
        key="opens_at",
        translation_key="opens_at",
        icon="mdi:door-open",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_opens_at,
    ),
    ChapultepecSensorDescription(
        key="closes_at",
        translation_key="closes_at",
        icon="mdi:door-closed",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_closes_at,
    ),
    ChapultepecSensorDescription(
        key="open_locations",
        translation_key="open_locations",
        icon="mdi:map-marker-check",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="locations",
        value_fn=lambda c: c.open_location_count(),
    ),
    ChapultepecSensorDescription(
        key="events_today",
        translation_key="events_today",
        icon="mdi:calendar-today",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="events",
        value_fn=_events_today,
    ),
    ChapultepecSensorDescription(
        key="next_event",
        translation_key="next_event",
        icon="mdi:calendar-star",
        value_fn=_next_event_value,
        attributes_fn=_next_event_attrs,
    ),
)


async def async_setup_entry(
    hass,
    entry: ChapultepecConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Chapultepec sensors."""
    coordinator = entry.runtime_data
    async_add_entities(ChapultepecSensor(coordinator, description) for description in SENSORS)


class ChapultepecSensor(ChapultepecEntity, SensorEntity):
    """A Chapultepec sensor driven by a value function."""

    entity_description: ChapultepecSensorDescription

    def __init__(self, coordinator: ChapultepecCoordinator, description: ChapultepecSensorDescription) -> None:
        """Initialise the sensor from its description."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType | datetime | date:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes, if the description defines them."""
        if self.entity_description.attributes_fn is None:
            return None
        return self.entity_description.attributes_fn(self.coordinator)
