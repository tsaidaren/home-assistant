"""The Griddy Power integration."""
import asyncio
from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers import aiohttp_client
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_LOADZONE, DOMAIN

LOAD_ZONES = ["LZ_HOUSTON", "LZ_WEST", "LZ_NORTH", "LZ_SOUTH"]

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({vol.Required(CONF_LOADZONE): cv.string})},
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Griddy Power component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Griddy Power from a config entry."""

    entry_data = entry.data

    async_griddy = AsyncGriddy(
        aiohttp_client.async_get_clientsession(hass),
        settlement_point=entry_data[CONF_LOADZONE],
    )

    async def async_update_data():
        """Fetch data from API endpoint."""
        return await async_griddy.async_getnow()

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="getnow",
        update_method=async_update_data,
        update_interval=timedelta(seconds=60),
    )

    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise PlatformNotReady

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry.entry_id, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


GETNOW_API_URL = "https://app.gogriddy.com/api/v1/insights/getnow"
DEFAULT_REQUEST_TIMEOUT = 15


class AsyncGriddy:
    """Async griddy api."""

    def __init__(
        self, websession, timeout=DEFAULT_REQUEST_TIMEOUT, settlement_point=None,
    ):
        """Create griddy async api object."""
        self._websession = websession
        self._settlement_point = settlement_point
        self._timeout = timeout

    async def async_getnow(self):
        """Call api to get the current price."""
        response = await self._websession.request(
            "post",
            GETNOW_API_URL,
            timeout=self._timeout,
            json={"settlement_point": self._settlement_point},
        )
        return await response.json()
