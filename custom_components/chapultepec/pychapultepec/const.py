"""Constants for the Attractions.io / Bosque de Chapultepec API.

The Bosque de Chapultepec app (``mx.bosquedechapultepec.aio``) is a white-label
build on the Attractions.io "Occasio" platform. Every venue is identified by a
single ``api_key``; all of the values below were recovered from the app's
``BuildConfig`` and bundled assets.
"""

from __future__ import annotations

# The public API key baked into the Chapultepec app's BuildConfig. It is not a
# secret in any meaningful sense: it identifies the venue and is required as the
# ``api-key`` component of every request's Authorization header.
DEFAULT_API_KEY = "402918a6-c7f1-48ec-b12a-bc64cb71232f"

# Bosque de Chapultepec is Resort record 262 in the dataset.
RESORT_ID = 262

# The map is delivered as a media item; its tiles live under ``<id>/textures/``.
MAP_MEDIA_ID = "c29a5cb0-7760-44a6-8f60-450d4ac34cc5"

# The park runs on Mexico City wall-clock time; all schedule datetimes are naive
# and interpreted in this zone.
DEFAULT_TIMEZONE = "America/Mexico_City"

# App identity sent during installation. Matches the reverse-engineered build.
APP_BUILD = 10
APP_VERSION = "1.0"
USER_AGENT = "pychapultepec"

# Endpoints.
API_BASE = "https://api.attractions.io/"
API_V1 = "https://api.attractions.io/v1/"
# Per-venue live data (opening hours / open-closed). Public, no auth.
LIVE_DATA_BASE = "https://live-data.attractions.io/"

# Event "tags" the Occasio engine recognises on scheduled items.
EVENT_TAGS = ("show", "talk", "feed", "activity", "tee", "event")
