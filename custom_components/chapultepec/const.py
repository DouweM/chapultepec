"""Constants for the Bosque de Chapultepec integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "chapultepec"

# Config / options keys.
CONF_API_KEY: Final = "api_key"
CONF_LANGUAGE: Final = "language"

# Default poll interval for the public live-data feed (open/closed + hours).
LIVE_UPDATE_INTERVAL: Final = timedelta(minutes=5)

# Instant events (a start time with no encoded duration) are shown in the
# calendar as a block of this length.
DEFAULT_EVENT_DURATION: Final = timedelta(hours=1)

# URL prefix under which the bundled map tiles are served.
TILES_URL_PREFIX: Final = f"/{DOMAIN}/tiles"

# Bundled data files (relative to the integration directory).
DATA_DIR: Final = "data"
TILES_DIR: Final = "tiles"
RECORDS_FILE: Final = "records.json"
MAP_MANIFEST_FILE: Final = "map_manifest.json"

LANGUAGES: Final = {"es-419": "Español", "en-US": "English"}
DEFAULT_LANGUAGE: Final = "es-419"

ATTRIBUTION: Final = "Data from the official Bosque de Chapultepec app (Fideicomiso Pro Bosque de Chapultepec)"
