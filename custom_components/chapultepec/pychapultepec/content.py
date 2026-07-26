"""In-memory content store built from a ``records.json`` dataset."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, tzinfo
from typing import Any

from .models import (
    Category,
    EventOccurrence,
    Poi,
    parse_category,
    parse_poi,
)
from .schedule import expand


class ContentStore:
    """Indexed view over the Attractions.io content dataset.

    Wraps the parsed ``records.json`` and exposes POIs, categories and expanded
    event occurrences, with filtering by category and item.
    """

    def __init__(self, records: dict[str, Any], tz: tzinfo, language: str | None = None) -> None:
        """Build indexes from a raw records mapping."""
        self._tz = tz
        self._language = language
        self._categories: dict[int, Category] = {
            raw["_id"]: parse_category(raw, language) for raw in records.get("Category", [])
        }
        self._pois: dict[int, Poi] = {raw["_id"]: parse_poi(raw, language) for raw in records.get("Item", [])}

    @property
    def categories(self) -> list[Category]:
        """All categories."""
        return list(self._categories.values())

    def category(self, category_id: int) -> Category | None:
        """Look up a category by id."""
        return self._categories.get(category_id)

    def poi(self, item_id: int) -> Poi | None:
        """Look up a POI by id."""
        return self._pois.get(item_id)

    def pois(
        self,
        *,
        category: int | Iterable[int] | None = None,
        visible_on_map: bool | None = None,
        scheduled: bool | None = None,
    ) -> list[Poi]:
        """Return POIs filtered by category, map visibility and schedule."""
        wanted = self._as_id_set(category)
        result: list[Poi] = []
        for poi in self._pois.values():
            if wanted is not None and not wanted.intersection(poi.category_ids):
                continue
            if visible_on_map is not None and poi.visible_on_map is not visible_on_map:
                continue
            if scheduled is not None and poi.is_scheduled is not scheduled:
                continue
            result.append(poi)
        return result

    def categories_for(self, poi: Poi) -> tuple[Category, ...]:
        """Resolve a POI's category ids into :class:`Category` objects."""
        return tuple(c for cid in poi.category_ids if (c := self._categories.get(cid)) is not None)

    def events(
        self,
        start: datetime,
        end: datetime,
        *,
        category: int | Iterable[int] | None = None,
        item_ids: int | Iterable[int] | None = None,
    ) -> list[EventOccurrence]:
        """Expand scheduled POIs into occurrences within ``[start, end)``.

        Optionally filter by ``category`` and/or specific ``item_ids``. Results
        are sorted by start time.
        """
        wanted_cats = self._as_id_set(category)
        wanted_items = self._as_id_set(item_ids)
        occurrences: list[EventOccurrence] = []
        for poi in self._pois.values():
            if poi.activity_times is None:
                continue
            if wanted_items is not None and poi.id not in wanted_items:
                continue
            if wanted_cats is not None and not wanted_cats.intersection(poi.category_ids):
                continue
            cats = self.categories_for(poi)
            for occ in expand(poi.activity_times, start, end, self._tz):
                occurrences.append(EventOccurrence(poi=poi, occurrence=occ, categories=cats))
        occurrences.sort(key=lambda e: (e.start, e.poi.name or ""))
        return occurrences

    @staticmethod
    def _as_id_set(value: int | Iterable[int] | None) -> set[int] | None:
        """Normalise an id / iterable-of-ids / None into a set or None."""
        if value is None:
            return None
        if isinstance(value, int):
            return {value}
        return set(value)
