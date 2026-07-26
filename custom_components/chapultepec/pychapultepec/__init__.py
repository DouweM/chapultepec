"""pychapultepec — an async SDK for the Bosque de Chapultepec (Attractions.io) app.

Reverse-engineered from the official ``mx.bosquedechapultepec.aio`` Android app.
Provides the venue's illustrated map metadata, point-of-interest content,
per-day event schedules and live open/closed status.
"""

from __future__ import annotations

from .client import ChapultepecClient
from .const import DEFAULT_API_KEY, DEFAULT_TIMEZONE, MAP_MEDIA_ID, RESORT_ID
from .content import ContentStore
from .exceptions import (
    ChapultepecConnectionError,
    ChapultepecError,
    ChapultepecParseError,
    ChapultepecRequestError,
)
from .models import (
    Category,
    EventOccurrence,
    ItemStatus,
    LiveStatus,
    MapInfo,
    Poi,
    localize,
)
from .schedule import Occurrence, expand

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_API_KEY",
    "DEFAULT_TIMEZONE",
    "MAP_MEDIA_ID",
    "RESORT_ID",
    "Category",
    "ChapultepecClient",
    "ChapultepecConnectionError",
    "ChapultepecError",
    "ChapultepecParseError",
    "ChapultepecRequestError",
    "ContentStore",
    "EventOccurrence",
    "ItemStatus",
    "LiveStatus",
    "MapInfo",
    "Occurrence",
    "Poi",
    "expand",
    "localize",
]
