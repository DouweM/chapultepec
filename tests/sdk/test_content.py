"""Tests for content parsing, filtering and event expansion."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from itertools import pairwise
from pathlib import Path
from zoneinfo import ZoneInfo

from pychapultepec import ContentStore, MapInfo

TZ = ZoneInfo("America/Mexico_City")
DATA = Path(__file__).resolve().parents[2] / "custom_components" / "chapultepec" / "data"


def _store() -> ContentStore:
    records = json.loads((DATA / "records.json").read_text(encoding="utf-8"))
    return ContentStore(records, TZ, language="es-419")


def test_pois_and_filters() -> None:
    """POIs load and can be filtered by map visibility and schedule."""
    store = _store()
    assert len(store.pois()) > 100
    assert all(p.visible_on_map for p in store.pois(visible_on_map=True))
    scheduled = store.pois(scheduled=True)
    assert scheduled and all(p.is_scheduled for p in scheduled)


def test_events_have_localized_names_and_locations() -> None:
    """Expanded events carry a Spanish name, categories and a location."""
    store = _store()
    now = datetime(2026, 7, 26, tzinfo=TZ)
    events = store.events(now, now + timedelta(days=1))
    assert events
    first = events[0]
    assert first.poi.name
    assert first.poi.location is not None
    # Sorted by start time.
    assert all(a.start <= b.start for a, b in pairwise(events))


def test_events_category_filter() -> None:
    """Filtering by category returns a subset only in that category."""
    store = _store()
    now = datetime(2026, 7, 26, tzinfo=TZ)
    all_events = store.events(now, now + timedelta(days=7))
    some_cat = next(iter(all_events[0].poi.category_ids))
    filtered = store.events(now, now + timedelta(days=7), category=some_cat)
    assert filtered
    assert all(some_cat in e.poi.category_ids for e in filtered)
    assert len(filtered) <= len(all_events)


def test_map_info_from_manifest() -> None:
    """Map manifest parses into sane geographic bounds around Chapultepec."""
    manifest = json.loads((DATA / "map_manifest.json").read_text(encoding="utf-8"))
    info = MapInfo.from_manifest(manifest)
    assert info.tile_size == 512
    assert (info.min_zoom, info.max_zoom) == (12, 18)
    south, west, north, east = info.bounds
    assert 19.3 < south < north < 19.5
    assert -99.3 < west < east < -99.1
    assert info.background_color.startswith("#")
