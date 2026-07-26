# Bosque de Chapultepec for Home Assistant

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

1. Add this repository as a custom repository (category: *Integration*).
2. Install **Bosque de Chapultepec**, restart Home Assistant.
3. *Settings → Devices & Services → Add Integration → Bosque de Chapultepec*.
   The default (public) API key is pre-filled; just pick a language.

### Manual

Copy `custom_components/chapultepec` into your HA `config/custom_components/`.

## Map dashboard card

Requires [ha-map-card](https://github.com/nathan-gs/ha-map-card). The tiles are
standard XYZ but 512 px, so `tileSize: 512` + `zoomOffset: -1` render the
illustration at its intended size while staying geographically aligned:

```yaml
type: custom:map-card
x: -99.187913   # park focal point
y: 19.420354
zoom: 15
tile_layer_url: /chapultepec/tiles/{z}.{x}.{y}.webp
tile_layer_options:
  tileSize: 512
  zoomOffset: -1
  minZoom: 13
  maxZoom: 21
  minNativeZoom: 13
  maxNativeZoom: 19
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
import aiohttp
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pychapultepec import ChapultepecClient, ContentStore, DEFAULT_TIMEZONE

tz = ZoneInfo(DEFAULT_TIMEZONE)

async with aiohttp.ClientSession() as session:
    client = ChapultepecClient(session)

    # Public, no auth: real-time open/closed + hours.
    live = await client.fetch_live_status()

    # Content (POIs, categories, events) — from a downloaded bundle.
    # (or load the bundled data/records.json directly)
    store = ContentStore(records, tz, language="es-419")

    # Events for today, filterable by category and/or item.
    now = datetime.now(tz)
    for ev in store.events(now, now + timedelta(days=1), category=6070):
        print(ev.start, ev.poi.name, [c.name for c in ev.categories])
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

## Legal

Data and map imagery are © the Fideicomiso Pro Bosque de Chapultepec, surfaced
here for personal use with attribution. Not affiliated with or endorsed by the
park or Attractions.io.
