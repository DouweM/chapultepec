"""Calendar of daily activities for Bosque de Chapultepec."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DEFAULT_EVENT_DURATION
from .coordinator import ChapultepecConfigEntry, ChapultepecCoordinator
from .entity import ChapultepecEntity
from .pychapultepec import EventOccurrence


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ChapultepecConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the activities calendar."""
    async_add_entities([ChapultepecCalendar(entry.runtime_data)])


class ChapultepecCalendar(ChapultepecEntity, CalendarEntity):
    """Exposes park activities (shows, talks, feeds, rides…) as a calendar."""

    _attr_translation_key = "activities"
    _attr_icon = "mdi:calendar-star"

    def __init__(self, coordinator: ChapultepecCoordinator) -> None:
        """Initialise the calendar entity."""
        super().__init__(coordinator, "activities")

    def _to_calendar_event(self, event: EventOccurrence) -> CalendarEvent:
        """Convert an occurrence into a Home Assistant calendar event."""
        end = event.start + DEFAULT_EVENT_DURATION if event.is_instant else event.end
        categories = ", ".join(c.name for c in event.categories if c.name)
        parts = [p for p in (event.poi.summary, f"({categories})" if categories else None) if p]
        description = " ".join(parts) or None
        location = None
        if event.poi.location:
            location = f"{event.poi.location[0]},{event.poi.location[1]}"
        return CalendarEvent(
            summary=event.poi.name or "Actividad",
            start=event.start,
            end=end,
            description=description,
            location=location,
            uid=f"{event.poi.id}-{int(event.start.timestamp())}",
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next upcoming activity."""
        now = datetime.now(self.coordinator.tz)
        upcoming = self.coordinator.events(now - timedelta(hours=12), now + timedelta(days=3))
        for occ in upcoming:
            end = occ.start + DEFAULT_EVENT_DURATION if occ.is_instant else occ.end
            if end >= now:
                return self._to_calendar_event(occ)
        return None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return activities within the requested window."""
        occurrences = self.coordinator.events(start_date, end_date)
        return [self._to_calendar_event(occ) for occ in occurrences]
