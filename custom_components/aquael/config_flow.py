"""Config flow to configure aquael component."""

from __future__ import annotations

from socket import gaierror
from typing import Any

from pyaquael import aquael
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    FlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_DEVICE_ID, CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import format_mac

from .const import (
    ATTR_COLOR_BLUE,
    ATTR_COLOR_RED,
    ATTR_COLOR_WHITE,
    DEFAULT_COLOR_BLUE,
    DEFAULT_COLOR_RED,
    DEFAULT_COLOR_WHITE,
    DOMAIN,
)

DATA_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})
OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_COLOR_RED, default=DEFAULT_COLOR_RED): vol.All(
            int, vol.Range(min=1, max=200)
        ),
        vol.Required(ATTR_COLOR_BLUE, default=DEFAULT_COLOR_BLUE): vol.All(
            int, vol.Range(min=1, max=200)
        ),
        vol.Required(ATTR_COLOR_WHITE, default=DEFAULT_COLOR_WHITE): vol.All(
            int, vol.Range(min=1, max=200)
        ),
    }
)


async def validate_input(hass: HomeAssistant, host: str) -> dict[str, Any]:
    """Validate that the user input allows us to connect."""
    light = aquael.Light(host)
    try:
        await light.async_test_connection()
    except (TimeoutError, gaierror):
        raise APIConnectionError

    name = await light.async_get_name()
    mac_address = await light.async_get_mac_address()

    return {"name": name, "mac_address": mac_address}


class AquaelFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle an aquael config flow."""

    VERSION = 1
    MINOR_VERSION = 0

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors = {}

        if user_input is not None:
            try:
                host = user_input[CONF_HOST]
                info = await validate_input(self.hass, host)

                name = info["name"]
                mac_address = info["mac_address"]

                unique_id = format_mac(mac_address)
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})

                return self.async_create_entry(
                    title=name,
                    data={CONF_NAME: name, CONF_HOST: host, CONF_DEVICE_ID: unique_id},
                )
            except APIConnectionError:
                errors["base"] = "connection_error"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlowHandler:
        """Create the options flow."""
        return OptionsFlowHandler()


class OptionsFlowHandler(OptionsFlow):
    """Handle an option flow for aquael."""

    VERSION = 1

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self.config_entry.options
            ),
        )


class APIConnectionError(HomeAssistantError):
    """Error to indicate we cannot connect."""
