"""The Bosque de Chapultepec integration.

Serves the park's illustrated basemap tiles, exposes live open/closed status as
sensors, and publishes the daily activity schedule as a calendar.
"""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import ChapultepecConfigEntry, ChapultepecCoordinator
from .http import async_register_tiles, register_map_view

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.CALENDAR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ChapultepecConfigEntry) -> bool:
    """Set up Bosque de Chapultepec from a config entry."""
    coordinator = ChapultepecCoordinator(hass, entry)
    await coordinator.async_load_content()
    # Non-raising refresh: the map and calendar come from bundled content, so a
    # transient live-data outage should not block setup (only the open/closed
    # sensors depend on it).
    await coordinator.async_refresh()
    entry.runtime_data = coordinator

    await async_register_tiles(hass)
    register_map_view(hass, coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ChapultepecConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
