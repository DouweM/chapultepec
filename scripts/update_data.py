#!/usr/bin/env python3
"""Refresh the bundled map tiles and content from the live Attractions.io API.

Downloads the full content bundle for the venue, then replaces the integration's
bundled map tiles, map manifest and records dataset in place. Run this whenever
the park updates its map or content:

    python scripts/update_data.py                 # default Chapultepec api key
    python scripts/update_data.py --api-key <key> # another Attractions.io venue

Requires ``aiohttp`` and ``python-dateutil`` (``pip install -e .``).
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INTEGRATION = REPO / "custom_components" / "chapultepec"
# Append (not insert) so the integration dir does not shadow stdlib modules
# such as `http`; `pychapultepec` is uniquely named and still resolves.
sys.path.append(str(INTEGRATION))

import aiohttp
from pychapultepec import DEFAULT_API_KEY, MAP_MEDIA_ID, ChapultepecClient


async def _download(api_key: str, dest: Path) -> None:
    """Download the content bundle for ``api_key`` to ``dest``."""
    async with aiohttp.ClientSession() as session:
        client = ChapultepecClient(session, api_key=api_key)
        print(f"Installing device for venue {api_key}…")
        await client.install()
        print("Downloading content bundle (this can be tens of MB)…")
        await client.download_bundle(dest)


def _extract(zip_path: Path) -> None:
    """Extract tiles, map manifest and records from the bundle into the repo."""
    tiles_dir = INTEGRATION / "tiles"
    data_dir = INTEGRATION / "data"
    map_prefix = f"media/{MAP_MEDIA_ID}/"

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()

        # Map tiles.
        tile_names = [n for n in names if n.startswith(map_prefix + "textures/") and n.endswith(".webp")]
        if not tile_names:
            raise SystemExit("No map tiles found in bundle — has the map id changed?")
        if tiles_dir.exists():
            shutil.rmtree(tiles_dir)
        tiles_dir.mkdir(parents=True)
        for name in tile_names:
            (tiles_dir / Path(name).name).write_bytes(zf.read(name))
        print(f"  tiles:        {len(tile_names)} -> {tiles_dir.relative_to(REPO)}")

        # Map manifest + routes.
        data_dir.mkdir(parents=True, exist_ok=True)
        _copy(zf, f"{map_prefix}manifest.json", data_dir / "map_manifest.json")
        _copy(zf, f"{map_prefix}routes.json", data_dir / "routes.json", optional=True)

        # Records dataset.
        _copy(zf, "records.json", data_dir / "records.json")


def _copy(zf: zipfile.ZipFile, name: str, dest: Path, *, optional: bool = False) -> None:
    """Copy a single member from the zip to ``dest``."""
    try:
        data = zf.read(name)
    except KeyError:
        if optional:
            return
        raise SystemExit(f"Bundle missing expected file: {name}") from None
    dest.write_bytes(data)
    print(f"  {dest.name:14}{len(data):>10,} bytes -> {dest.relative_to(REPO)}")


async def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="Attractions.io venue api key")
    parser.add_argument("--keep-zip", action="store_true", help="keep the downloaded bundle zip")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "bundle.zip"
        await _download(args.api_key, zip_path)
        print(f"Downloaded {zip_path.stat().st_size / 1e6:.1f} MB; extracting…")
        _extract(zip_path)
        if args.keep_zip:
            kept = REPO / "bundle.zip"
            shutil.copy2(zip_path, kept)
            print(f"Kept bundle at {kept}")
    print("Done. Review the diff and commit the refreshed tiles/data.")


if __name__ == "__main__":
    asyncio.run(_main())
