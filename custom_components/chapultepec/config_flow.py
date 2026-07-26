"""Config flow for the Bosque de Chapultepec integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_API_KEY,
    CONF_LANGUAGE,
    DEFAULT_LANGUAGE,
    DOMAIN,
    LANGUAGES,
)
from .pychapultepec import DEFAULT_API_KEY, ChapultepecClient
from .pychapultepec.exceptions import ChapultepecError

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY, default=DEFAULT_API_KEY): str,
        vol.Required(CONF_LANGUAGE, default=DEFAULT_LANGUAGE): SelectSelector(
            SelectSelectorConfig(
                mode=SelectSelectorMode.DROPDOWN,
                options=[SelectOptionDict(value=code, label=name) for code, name in LANGUAGES.items()],
            )
        ),
    }
)


class ChapultepecConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Bosque de Chapultepec."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY]
            await self.async_set_unique_id(api_key)
            self._abort_if_unique_id_configured()

            client = ChapultepecClient(async_get_clientsession(self.hass), api_key=api_key)
            try:
                await client.fetch_live_status()
            except ChapultepecError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error validating Chapultepec api key")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title="Bosque de Chapultepec", data=user_input)

        return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors)
