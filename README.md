# Bosque de Chapultepec for Home Assistant

[![CI](https://github.com/DouweM/chapultepec/actions/workflows/ci.yml/badge.svg)](https://github.com/DouweM/chapultepec/actions/workflows/ci.yml)
[![hacs](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)

A Home Assistant integration (and companion Python SDK, `pychapultepec`) for the
official **Bosque de Chapultepec** app — Mexico City's great park. It brings the
app's beautiful illustrated map, live open/closed status, and daily activity
schedule into Home Assistant.

The app is a white-label build on the [Attractions.io](https://attractions.io)
"Occasio" platform; everything here was reverse-engineered from the public
`mx.bosquedechapultepec.aio` Android app and its (public) content APIs.

## Features

- **Illustrated basemap**, self-hosted. The park's hand-drawn map is shipped as
  ~1,500 512 px Web-Mercator tiles (zoom 12–18) and served by the integration at
  `/chapultepec/tiles/{z}.{x}.{y}.webp`, ready to drop into a Lovelace map card.
- **Live status sensors** from the park's public live-data feed:
  - `binary_sensor.…_park_open` — is the park open now
  - `sensor.…_opens_at` / `…_closes_at` — today's hours
  - `sensor.…_open_locations` — how many attractions are open right now
  - `sensor.…_events_today` / `…_next_event`
- **Activities calendar** (`calendar.…_activities`) — the daily programme
  (shows, talks, feedings, rides, workshops…), expanded from each attraction's
  recurring schedule.

## Install

### HACS (recommended)

1. In HACS → *Custom repositories*, add `https://github.com/DouweM/chapultepec`
   (category: *Integration*).
2. Install **Bosque de Chapultepec**, restart Home Assistant.
3. *Settings → Devices & Services → Add Integration → Bosque de Chapultepec*.
   The default (public) API key is pre-filled; just pick a language.

### Manual

Copy `custom_components/chapultepec` into your HA `config/custom_components/`.

## Map dashboard card

Requires [ha-map-card](https://github.com/nathan-gs/ha-map-card). The tiles are
standard Web-Mercator XYZ (512 px hi-res), so the normal tile scheme applies.
Note that `ha-map-card` takes `x` as **latitude** and `y` as **longitude** (it
passes `[x, y]` straight to Leaflet's `setView([lat, lng])`):

```yaml
type: custom:map-card
x: 19.420354    # latitude  (park focal point)
y: -99.187913   # longitude
zoom: 15
tile_layer_url: /chapultepec/tiles/{z}.{x}.{y}.webp
tile_layer_options:
  detectRetina: false
  minNativeZoom: 12
  maxNativeZoom: 18
  maxZoom: 21
entities:
  - person.you        # markers show if you're in the park
```

The integration also exposes the tileset metadata (bounds, center, tile URL,
background colour) as JSON at `/chapultepec/map`.

## Updating the map & data

The bundled tiles/data are a snapshot. To refresh from the live API (the park
occasionally redraws the map or adds attractions):

```bash
pip install -e .
python scripts/update_data.py        # re-extracts tiles, records, map manifest
# review the diff, then commit
```

## SDK usage

`pychapultepec` is a standalone async SDK; the integration vendors it.

```python
import aiohttp, json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pychapultepec import ChapultepecClient, ContentStore, DEFAULT_TIMEZONE

tz = ZoneInfo(DEFAULT_TIMEZONE)

async with aiohttp.ClientSession() as session:
    client = ChapultepecClient(session)

    # Public, no auth: real-time open/closed + hours.
    live = await client.fetch_live_status()
    print("open now:", sum(bool(i.is_open) for i in live.items.values()))

    # Content (POIs, categories, events). Use the bundled snapshot, or fetch a
    # fresh bundle with `await client.download_bundle(path)` and unzip records.json.
    records = json.load(open("custom_components/chapultepec/data/records.json"))
    store = ContentStore(records, tz, language="es-419")

    # Events today, filterable by category (6070 = Actividades) and/or item id.
    now = datetime.now(tz)
    for ev in store.events(now, now + timedelta(days=1), category=6070):
        print(ev.start.strftime("%H:%M"), ev.poi.name, [c.name for c in ev.categories])
```

## How it works

| Concern | Source |
| --- | --- |
| Auth | `Attractions-Io api-key="<key>", installation-token="<token>"` after a `POST /v1/installation` |
| Content bundle | `GET /v1/data` → presigned S3 zip (records + media + map tiles) |
| Live status | `GET https://live-data.attractions.io/<key>.json` (public) |
| Events | `Item.ActivityTimes`, a temporal set-algebra expanded per day |
| Map | media item `c29a5cb0…`, `textures/{z}.{x}.{y}.webp`, 512 px, XYZ |

Note: `api.attractions.io/v3/events` is the app's *analytics* telemetry, not park
events — it is deliberately not used.

## Development

```bash
uv sync --group dev
uv run pytest tests/sdk                              # SDK unit tests (no HA needed)
uv pip install homeassistant pytest-homeassistant-custom-component
uv run pytest tests/integration                      # HA setup test (run separately)
uv run ruff check . && uv run ruff format --check .  # lint
```

The HA integration test lives under `tests/integration` and is run separately
from the SDK tests: the Home Assistant pytest plugin installs global autouse
fixtures that assume a running event loop, which is incompatible with plain sync
unit tests in the same session.

## Legal

Data and map imagery are © the Fideicomiso Pro Bosque de Chapultepec, surfaced
here for personal use with attribution. Not affiliated with or endorsed by the
park or Attractions.io.
