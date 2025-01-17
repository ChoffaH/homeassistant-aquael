"""Platform for light integration."""

from asyncio import TimeoutError
import logging

from pyaquael import aquael

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_ID, CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_COLOR_BLUE,
    ATTR_COLOR_RED,
    ATTR_COLOR_WHITE,
    DEFAULT_COLOR_BLUE,
    DEFAULT_COLOR_RED,
    DEFAULT_COLOR_WHITE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add light for passed config_entry in HA."""
    host = config_entry.data[CONF_HOST]
    name = config_entry.data[CONF_NAME]
    device_id = config_entry.data[CONF_DEVICE_ID]
    light = aquael.Light(host)
    options = {
        ATTR_COLOR_RED: config_entry.options.get(ATTR_COLOR_RED, DEFAULT_COLOR_RED),
        ATTR_COLOR_BLUE: config_entry.options.get(ATTR_COLOR_BLUE, DEFAULT_COLOR_BLUE),
        ATTR_COLOR_WHITE: config_entry.options.get(
            ATTR_COLOR_WHITE, DEFAULT_COLOR_WHITE
        ),
    }

    try:
        await light.async_test_connection()
    except TimeoutError as ex:
        raise ConfigEntryNotReady(f"Timed out while connecting to {light.host}") from ex

    async_add_entities([LeddySlimLinkLight(name, device_id, light, options)], True)


class LeddySlimLinkLight(LightEntity):
    """Representation of a Leddy Slim Link light."""

    def __init__(
        self, name: str, device_id: str, light: aquael.Light, options: dict[str, int]
    ) -> None:
        """Initialize a LeddySlimLink."""
        self._light = light
        self._options = options

        self._attr_is_on = light.is_on
        self._attr_brightness = light.brightness
        self._attr_name = name
        self._attr_unique_id = f"{device_id}_light"

    @property
    def color_mode(self):
        """Return the color mode of the light."""
        return ColorMode.BRIGHTNESS

    @property
    def supported_color_modes(self):
        """Flag supported color modes."""
        return {ColorMode.BRIGHTNESS}

    def _compute_brightness(self) -> int:
        """Compute the brightness based on the current color of the light and the configured color value."""
        max_red = self._options[ATTR_COLOR_RED]
        max_blue = self._options[ATTR_COLOR_BLUE]
        max_white = self._options[ATTR_COLOR_WHITE]

        red_brightness = self._light.colors[0] / max_red
        blue_brightness = self._light.colors[1] / max_blue
        white_brightness = self._light.colors[2] / max_white

        return min(min(red_brightness, blue_brightness, white_brightness) * 255, 255)

    async def async_turn_on(self, **kwargs):
        """Instruct the light to turn on."""
        try:
            red = self._options[ATTR_COLOR_RED]
            blue = self._options[ATTR_COLOR_BLUE]
            white = self._options[ATTR_COLOR_WHITE]

            self._light.brightness = kwargs.get(ATTR_BRIGHTNESS, 255)

            await self._light.async_turn_on(red, blue, white)
        except Exception as error:
            _LOGGER.error("Error while turning on %s: %s", self.entity_id, error)

    async def async_turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        try:
            await self._light.async_turn_off()
        except Exception as error:
            _LOGGER.error("Error while turning off %s: %s", self.entity_id, error)

    async def async_update(self):
        """Update entity state."""
        try:
            await self._light.async_update()
        except TimeoutError:
            if self.available:
                _LOGGER.warning("Update timed out for %s", self.entity_id)
            self._attr_available = False
            return
        except Exception as error:
            _LOGGER.error("Error while updating %s: %s", self.entity_id, error)
            return

        self._attr_available = True
        self._attr_is_on = self._light.is_on
        self._attr_brightness = self._compute_brightness()
