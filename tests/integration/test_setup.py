"""Integration setup smoke test using a real Home Assistant instance."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pychapultepec import DEFAULT_API_KEY
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.chapultepec.const import CONF_API_KEY, CONF_LANGUAGE, DOMAIN


@pytest.fixture(autouse=True)
def _enable(enable_custom_integrations):
    """Enable loading the custom integration in tests."""
    return


async def test_setup_creates_entities(hass: HomeAssistant, aioclient_mock) -> None:
    """The integration sets up and creates its sensors and calendar."""
    aioclient_mock.get(
        f"https://live-data.attractions.io/{DEFAULT_API_KEY}.json",
        json={
            "entities": {
                "Resort": {
                    "records": [
                        {
                            "_id": 262,
                            "OpeningTimes": '{"type":"range","start":"2026-07-26 05:00:00","end":"2026-07-26 18:00:00"}',
                        }
                    ]
                },
                "Item": {"records": [{"_id": 47717, "IsOpen": True, "IsOperational": True, "OpeningTimes": None}]},
            }
        },
    )
    assert await async_setup_component(hass, "http", {})
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: DEFAULT_API_KEY, CONF_LANGUAGE: "es-419"},
        unique_id=DEFAULT_API_KEY,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("calendar.bosque_de_chapultepec_activities") is not None
    assert hass.states.get("sensor.bosque_de_chapultepec_open_locations") is not None
    assert hass.states.get("binary_sensor.bosque_de_chapultepec_park_open") is not None
