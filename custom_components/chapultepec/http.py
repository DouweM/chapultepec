"""HTTP surface for the Chapultepec integration: static map tiles + map info."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from aiohttp import web
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.core import HomeAssistant, callback

from .const import ATTRIBUTION, DOMAIN, TILES_DIR, TILES_URL_PREFIX

if TYPE_CHECKING:
    from .coordinator import ChapultepecCoordinator

_TILES_REGISTERED = f"{DOMAIN}_tiles_registered"
_MAP_VIEW_REGISTERED = f"{DOMAIN}_map_view_registered"
MAP_INFO_URL = f"/{DOMAIN}/map"


async def async_register_tiles(hass: HomeAssistant) -> None:
    """Serve the bundled map tiles as static files (once)."""
    if hass.data.get(_TILES_REGISTERED):
        return
    tiles_dir = Path(__file__).parent / TILES_DIR
    await hass.http.async_register_static_paths(
        [StaticPathConfig(TILES_URL_PREFIX, str(tiles_dir), cache_headers=True)]
    )
    hass.data[_TILES_REGISTERED] = True


@callback
def register_map_view(hass: HomeAssistant, coordinator: ChapultepecCoordinator) -> None:
    """Register the map-info JSON endpoint (once)."""
    if hass.data.get(_MAP_VIEW_REGISTERED):
        return
    hass.http.register_view(ChapultepecMapView(coordinator))
    hass.data[_MAP_VIEW_REGISTERED] = True


class ChapultepecMapView(HomeAssistantView):
    """Expose the map tileset metadata (bounds, zoom, tile URL) as JSON.

    Handy for wiring up a Lovelace map card without hardcoding values.
    """

    url = MAP_INFO_URL
    name = f"api:{DOMAIN}:map"
    requires_auth = False

    def __init__(self, coordinator: ChapultepecCoordinator) -> None:
        """Store the coordinator holding the parsed map metadata."""
        self._coordinator = coordinator

    async def get(self, request: web.Request) -> web.Response:
        """Return the map metadata JSON."""
        info = self._coordinator.map_info
        if info is None:
            return web.json_response({"error": "map not loaded"}, status=503)
        south, west, north, east = info.bounds
        return web.json_response(
            {
                "tile_url": f"{TILES_URL_PREFIX}/{{z}}.{{x}}.{{y}}.{info.tile_format}",
                "tile_size": info.tile_size,
                "min_zoom": info.min_zoom,
                "max_zoom": info.max_zoom,
                "background_color": info.background_color,
                "center": {"latitude": info.center[0], "longitude": info.center[1]},
                "bounds": {"south": south, "west": west, "north": north, "east": east},
                "attribution": ATTRIBUTION,
            }
        )
