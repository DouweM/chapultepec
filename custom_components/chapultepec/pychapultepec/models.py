"""Data models for Bosque de Chapultepec content and live status."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .schedule import Occurrence

# Preferred language order when resolving localized strings. The park is in
# Mexico City, so Latin-American Spanish first.
_LOCALE_ORDER = ("es-419", "es", "es-US", "en-US", "en")


def localize(value: Any, language: str | None = None) -> str | None:
    """Resolve a localized ``{locale: text}`` field to a single string."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        order = ((language,) if language else ()) + _LOCALE_ORDER
        for locale in order:
            if locale and value.get(locale):
                return value[locale]
        # Fall back to any populated value.
        for candidate in value.values():
            if candidate:
                return candidate
    return None


def _parse_location(value: Any) -> tuple[float, float] | None:
    """Parse a ``"lat,lng"`` string into a ``(lat, lng)`` tuple."""
    if not value or not isinstance(value, str):
        return None
    try:
        lat, lng = (float(part) for part in value.split(","))
    except ValueError:
        return None
    return (lat, lng)


@dataclass(frozen=True)
class Category:
    """A content category (e.g. Entretenimiento, Actividades)."""

    id: int
    name: str | None
    icon: str | None = None
    parent: int | None = None


@dataclass(frozen=True)
class Poi:
    """A point of interest (Attractions.io ``Item``)."""

    id: int
    name: str | None
    summary: str | None
    location: tuple[float, float] | None
    category_ids: tuple[int, ...]
    default_image: str | None
    visible_on_map: bool
    activity_times: dict[str, Any] | None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def is_scheduled(self) -> bool:
        """Whether this POI carries an event schedule."""
        return self.activity_times is not None


@dataclass(frozen=True)
class EventOccurrence:
    """A single scheduled occurrence of a POI's activity."""

    poi: Poi
    occurrence: Occurrence
    categories: tuple[Category, ...]

    @property
    def start(self) -> datetime:
        """Start time of the occurrence."""
        return self.occurrence.start

    @property
    def end(self) -> datetime:
        """End time of the occurrence (equals start for instants)."""
        return self.occurrence.end

    @property
    def is_instant(self) -> bool:
        """Whether the occurrence is a point in time (a start with no duration)."""
        return self.occurrence.is_instant


@dataclass(frozen=True)
class OpeningHours:
    """A resolved opening window for today (from live data)."""

    start: datetime
    end: datetime


@dataclass(frozen=True)
class ItemStatus:
    """Live status for a single item."""

    id: int
    is_open: bool | None
    is_operational: bool | None
    opening_times: dict[str, Any] | None


@dataclass(frozen=True)
class LiveStatus:
    """Live status snapshot from the public live-data feed."""

    resort_opening_times: dict[str, Any] | None
    items: dict[int, ItemStatus]
    raw: dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass(frozen=True)
class MapInfo:
    """Metadata describing the illustrated basemap tileset."""

    tile_path: str  # e.g. "textures/{z}.{x}.{y}.webp"
    tile_format: str
    tile_size: int
    min_zoom: int
    max_zoom: int
    background_color: str
    bounds: tuple[float, float, float, float]  # SW lat, SW lng, NE lat, NE lng
    center: tuple[float, float]  # lat, lng

    @classmethod
    def from_manifest(cls, manifest: dict[str, Any]) -> MapInfo:
        """Build ``MapInfo`` from a map media ``manifest.json``."""
        import math

        textures = manifest["textures"]
        extent = manifest["extent"]
        b = manifest["bounds"]

        def _merc_to_lat(y: float) -> float:
            return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y))))

        def _merc_to_lng(x: float) -> float:
            return x * 360.0 - 180.0

        west = _merc_to_lng(b["left"])
        east = _merc_to_lng(b["left"] + b["width"])
        north = _merc_to_lat(b["top"])
        south = _merc_to_lat(b["top"] + b["height"])
        return cls(
            tile_path=textures["path"],
            tile_format=textures.get("format", "webp"),
            tile_size=textures.get("size", 512),
            min_zoom=extent.get("minZoom", 12),
            max_zoom=extent.get("maxZoom", 18),
            background_color="#" + textures.get("backgroundColor", "83ba77").lstrip("#"),
            bounds=(south, west, north, east),
            center=((north + south) / 2, (west + east) / 2),
        )


def parse_category(raw: dict[str, Any], language: str | None = None) -> Category:
    """Build a :class:`Category` from a raw record."""
    return Category(
        id=raw["_id"],
        name=localize(raw.get("Name"), language),
        icon=raw.get("Icon"),
        parent=raw.get("Parent"),
    )


def parse_poi(raw: dict[str, Any], language: str | None = None) -> Poi:
    """Build a :class:`Poi` from a raw ``Item`` record."""
    import json

    activity = raw.get("ActivityTimes")
    parsed_activity = json.loads(activity) if isinstance(activity, str) else activity
    category = raw.get("Category")
    if isinstance(category, int):
        category_ids: tuple[int, ...] = (category,)
    elif isinstance(category, list):
        category_ids = tuple(category)
    else:
        category_ids = ()
    return Poi(
        id=raw["_id"],
        name=localize(raw.get("Name"), language),
        summary=localize(raw.get("Summary"), language),
        location=_parse_location(raw.get("Location")),
        category_ids=category_ids,
        default_image=raw.get("DefaultImage"),
        visible_on_map=bool(raw.get("VisibleOnMap", True)),
        activity_times=parsed_activity,
        raw=raw,
    )
