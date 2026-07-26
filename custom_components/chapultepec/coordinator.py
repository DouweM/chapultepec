"""Data update coordinator for the Bosque de Chapultepec integration."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_API_KEY,
    CONF_LANGUAGE,
    DATA_DIR,
    DEFAULT_LANGUAGE,
    DOMAIN,
    LIVE_UPDATE_INTERVAL,
    MAP_MANIFEST_FILE,
    RECORDS_FILE,
)
from .pychapultepec import (
    DEFAULT_API_KEY,
    DEFAULT_TIMEZONE,
    ChapultepecClient,
    ContentStore,
    EventOccurrence,
    LiveStatus,
    MapInfo,
)
from .pychapultepec.exceptions import ChapultepecError
from .pychapultepec.schedule import expand

_LOGGER = logging.getLogger(__name__)

type ChapultepecConfigEntry = ConfigEntry[ChapultepecCoordinator]


class ChapultepecCoordinator(DataUpdateCoordinator[LiveStatus]):
    """Loads bundled content once and polls the public live-data feed."""

    def __init__(self, hass: HomeAssistant, entry: ChapultepecConfigEntry) -> None:
        """Set up the coordinator for a config entry."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=LIVE_UPDATE_INTERVAL,
        )
        api_key = entry.data.get(CONF_API_KEY, DEFAULT_API_KEY)
        self._language = entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)
        self.tz = ZoneInfo(DEFAULT_TIMEZONE)
        self.client = ChapultepecClient(async_get_clientsession(hass), api_key=api_key)
        self._base = Path(__file__).parent / DATA_DIR
        self.store: ContentStore | None = None
        self.map_info: MapInfo | None = None

    async def async_load_content(self) -> None:
        """Load the bundled records and map manifest from disk (once)."""
        store, map_info = await self.hass.async_add_executor_job(self._load_content)
        self.store = store
        self.map_info = map_info

    def _load_content(self) -> tuple[ContentStore, MapInfo]:
        """Read and parse bundled content files (runs in an executor)."""
        records = json.loads((self._base / RECORDS_FILE).read_text(encoding="utf-8"))
        manifest = json.loads((self._base / MAP_MANIFEST_FILE).read_text(encoding="utf-8"))
        return (
            ContentStore(records, self.tz, language=self._language),
            MapInfo.from_manifest(manifest),
        )

    async def _async_update_data(self) -> LiveStatus:
        """Fetch the latest live status from the public feed."""
        try:
            return await self.client.fetch_live_status()
        except ChapultepecError as err:
            raise UpdateFailed(str(err)) from err

    # -- Derived helpers -----------------------------------------------------

    def resort_hours_today(self, now: datetime | None = None) -> tuple[datetime, datetime] | None:
        """Return today's (open, close) for the whole park, if published."""
        times = self.data.resort_opening_times if self.data else None
        if not times:
            return None
        now = now or datetime.now(self.tz)
        occurrences = expand(
            times, now.replace(hour=0, minute=0, second=0, microsecond=0), now.replace(hour=23, minute=59), self.tz
        )
        if not occurrences:
            return None
        occ = occurrences[0]
        return (occ.start, occ.end)

    def is_park_open(self, now: datetime | None = None) -> bool | None:
        """Whether the park is open at ``now`` per today's published hours."""
        hours = self.resort_hours_today(now)
        if hours is None:
            return None
        now = (now or datetime.now(self.tz)).astimezone(self.tz)
        return hours[0] <= now < hours[1]

    def open_location_count(self) -> int:
        """Count of locations currently flagged open in live data."""
        if not self.data:
            return 0
        return sum(1 for item in self.data.items.values() if item.is_open)

    def events(self, start: datetime, end: datetime, **filters: object) -> list[EventOccurrence]:
        """Expand events over a window (delegates to the content store)."""
        if self.store is None:
            return []
        return self.store.events(start, end, **filters)  # type: ignore[arg-type]

    def next_event(self, now: datetime | None = None) -> EventOccurrence | None:
        """Return the next event starting at/after ``now`` (within ~2 days)."""
        from datetime import timedelta

        now = now or datetime.now(self.tz)
        upcoming = self.events(now, now + timedelta(days=2))
        for event in upcoming:
            if event.start >= now:
                return event
        return upcoming[0] if upcoming else None
