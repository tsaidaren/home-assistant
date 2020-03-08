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

from .const import CONF_MEMBER_ID, CONF_METER_ID, CONF_SETTLEMENT_POINT, DOMAIN

_LOGGER = logging.getLogger(__name__)

# , UpdateFailed


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_MEMBER_ID): cv.positive_int,
                vol.Required(CONF_METER_ID): cv.positive_int,
                vol.Required(CONF_SETTLEMENT_POINT): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Griddy Power component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Griddy Power from a config entry."""

    entry_data = entry.data

    member_id = entry_data[CONF_MEMBER_ID]
    meter_id = entry_data[CONF_METER_ID]
    settlement_point = entry_data[CONF_SETTLEMENT_POINT]
    async_griddy = AsyncGriddy(
        aiohttp_client.async_get_clientsession(hass),
        member_id=member_id,
        meter_id=meter_id,
        settlement_point=settlement_point,
    )

    async def async_update_data():
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
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
    def __init__(
        self,
        websession,
        timeout=DEFAULT_REQUEST_TIMEOUT,
        member_id=None,
        meter_id=None,
        settlement_point=None,
    ):
        self._websession = websession
        self._member_id = member_id
        self._meter_id = meter_id
        self._settlement_point = settlement_point
        self._timeout = timeout

    async def async_getnow(self, member_id, meter_id, settlement_point):
        response = await self._websession.request(
            "post",
            GETNOW_API_URL,
            timeout=self._timeout,
            json={
                "meterID": self._meter_id,
                "memberID": self._member_id,
                "settlement_point": self._settlement_point,
            },
        )
        return await response.json()
