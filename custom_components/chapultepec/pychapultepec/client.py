"""Async client for the Attractions.io API used by the Chapultepec app."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiohttp

from .const import (
    API_V1,
    APP_BUILD,
    APP_VERSION,
    DEFAULT_API_KEY,
    LIVE_DATA_BASE,
    USER_AGENT,
)
from .exceptions import (
    ChapultepecConnectionError,
    ChapultepecParseError,
    ChapultepecRequestError,
)
from .models import ItemStatus, LiveStatus


def _http_date(now: datetime | None = None) -> str:
    """Return an RFC-1123 date string, required by the ``/v1/data`` endpoint."""
    now = now or datetime.now(UTC)
    return now.strftime("%a, %d %b %Y %H:%M:%S GMT")


class ChapultepecClient:
    """Talks to the Attractions.io backend for a single venue (api key).

    The only stateful concern is the installation token, obtained lazily on
    first use of an authenticated endpoint and cached for the client's lifetime.
    The live-data feed needs no authentication at all.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        *,
        api_key: str = DEFAULT_API_KEY,
        device_id: str | None = None,
        installation_token: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        """Create a client bound to an aiohttp session and venue api key."""
        self._session = session
        self._api_key = api_key
        self._device_id = device_id or str(uuid.uuid4())
        self._installation_token = installation_token
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    @property
    def api_key(self) -> str:
        """The venue api key in use."""
        return self._api_key

    @property
    def device_id(self) -> str:
        """The device identifier used for installation."""
        return self._device_id

    @property
    def installation_token(self) -> str | None:
        """The cached installation token, if the client has installed."""
        return self._installation_token

    def _auth_header(self, *, with_installation: bool) -> str:
        """Build the ``Attractions-Io`` Authorization header."""
        if with_installation:
            return f'Attractions-Io api-key="{self._api_key}", installation-token="{self._installation_token}"'
        return f'Attractions-Io api-key="{self._api_key}"'

    async def install(self, *, force: bool = False) -> str:
        """Register this device and return an installation token.

        The token is cached; pass ``force=True`` to re-register.
        """
        if self._installation_token and not force:
            return self._installation_token

        form = aiohttp.FormData()
        form.add_field("device_identifier", self._device_id)
        form.add_field("app_build", str(APP_BUILD))
        form.add_field("app_version", APP_VERSION)
        headers = {
            "Authorization": self._auth_header(with_installation=False),
            "Idempotency-Key": str(uuid.uuid4()),
            "User-Agent": USER_AGENT,
        }
        try:
            async with self._session.post(
                f"{API_V1}installation", data=form, headers=headers, timeout=self._timeout
            ) as resp:
                body = await resp.text()
                if resp.status not in (200, 201):
                    raise ChapultepecRequestError(
                        f"Installation failed: HTTP {resp.status}", status=resp.status, body=body
                    )
                import json

                token = json.loads(body).get("token")
        except aiohttp.ClientError as err:
            raise ChapultepecConnectionError(f"Installation request failed: {err}") from err
        if not token:
            raise ChapultepecParseError("Installation response missing token")
        self._installation_token = token
        return token

    async def download_bundle(self, dest: Path, *, version: str | None = None) -> Path:
        """Download the full content bundle (records + media + map tiles) as a zip.

        Installs first if necessary. ``version`` may be a previous manifest
        version to request a delta bundle. Returns ``dest``.
        """
        await self.install()
        params = {"version": version} if version else None
        headers = {
            "Authorization": self._auth_header(with_installation=True),
            "Idempotency-Key": str(uuid.uuid4()),
            "Date": _http_date(),
            "User-Agent": USER_AGENT,
        }
        # A long timeout: the bundle is tens of MB.
        timeout = aiohttp.ClientTimeout(total=600)
        try:
            async with self._session.get(
                f"{API_V1}data", params=params, headers=headers, timeout=timeout, allow_redirects=True
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise ChapultepecRequestError(
                        f"Bundle download failed: HTTP {resp.status}", status=resp.status, body=body
                    )
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open("wb") as fh:
                    async for chunk in resp.content.iter_chunked(1 << 16):
                        fh.write(chunk)
        except aiohttp.ClientError as err:
            raise ChapultepecConnectionError(f"Bundle download failed: {err}") from err
        return dest

    async def fetch_live_status(self) -> LiveStatus:
        """Fetch the public live-data feed (opening hours / open-closed)."""
        url = f"{LIVE_DATA_BASE}{self._api_key}.json"
        try:
            async with self._session.get(url, timeout=self._timeout) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise ChapultepecRequestError(
                        f"Live-data fetch failed: HTTP {resp.status}", status=resp.status, body=body
                    )
                payload = await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise ChapultepecConnectionError(f"Live-data fetch failed: {err}") from err
        return self._parse_live_status(payload)

    @staticmethod
    def _parse_live_status(payload: dict[str, Any]) -> LiveStatus:
        """Parse the live-data JSON payload into a :class:`LiveStatus`."""
        entities = payload.get("entities", {})
        resort_records = entities.get("Resort", {}).get("records", [])
        resort_times = resort_records[0].get("OpeningTimes") if resort_records else None
        if isinstance(resort_times, str):
            import json

            resort_times = json.loads(resort_times)

        items: dict[int, ItemStatus] = {}
        for record in entities.get("Item", {}).get("records", []):
            opening = record.get("OpeningTimes")
            if isinstance(opening, str):
                import json

                opening = json.loads(opening)
            items[record["_id"]] = ItemStatus(
                id=record["_id"],
                is_open=record.get("IsOpen"),
                is_operational=record.get("IsOperational"),
                opening_times=opening,
            )
        return LiveStatus(resort_opening_times=resort_times, items=items, raw=payload)
