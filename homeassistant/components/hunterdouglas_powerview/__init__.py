"""The Hunter Douglas PowerView integration."""
import asyncio
from datetime import timedelta
import logging

from aiopvapi.helpers.aiorequest import AioRequest
from aiopvapi.helpers.constants import ATTR_ID
from aiopvapi.rooms import Rooms
from aiopvapi.scenes import Scenes
from aiopvapi.shades import Shades
import async_timeout
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    COORDINATOR,
    DOMAIN,
    HUB_ADDRESS,
    PV_API,
    PV_ROOM_DATA,
    PV_ROOMS,
    PV_SCENE_DATA,
    PV_SCENES,
    PV_SHADE_DATA,
    PV_SHADES,
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({vol.Required(HUB_ADDRESS): cv.string})}, extra=vol.ALLOW_EXTRA
)

PLATFORMS = ["cover", "scene"]
_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Hunter Douglas PowerView component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Hunter Douglas PowerView from a config entry."""

    config = entry.data

    hub_address = config.get(HUB_ADDRESS)
    websession = async_get_clientsession(hass)

    pv_request = AioRequest(hub_address, loop=hass.loop, websession=websession)

    rooms = Rooms(pv_request)
    room_entries = await rooms.get_resources()
    _LOGGER.debug("Room entries: %s", room_entries)
    if not room_entries:
        _LOGGER.error("Unable to initialize PowerView hub: %s", hub_address)
        raise ConfigEntryNotReady
    room_data = map_data_by_id(room_entries)
    _LOGGER.debug("Room data: %s", room_data)

    scenes = Scenes(pv_request)
    scene_entries = await scenes.get_resources()
    _LOGGER.debug("Scene entries: %s", scene_entries)
    scene_data = map_data_by_id(scene_entries)
    _LOGGER.debug("Scene data: %s", scene_data)

    shades = Shades(pv_request)
    shade_entries = await shades.get_resources()
    _LOGGER.debug("Shade entries: %s", shade_entries)
    shade_data = map_data_by_id(shade_entries)
    _LOGGER.debug("Shade data: %s", shade_data)

    async def async_update_data():
        """Fetch data from shade endpoint."""
        async with async_timeout.timeout(10):
            shade_entries = await hass.data[DOMAIN][entry.entry_id][
                PV_SHADES
            ].get_resources()
        if not shade_entries:
            raise UpdateFailed(f"Failed to fetch new shade data.")
        shade_data = map_data_by_id(shade_entries)
        hass.data[DOMAIN][entry.entry_id][PV_SHADE_DATA] = shade_data

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="powerview hub",
        update_method=async_update_data,
        update_interval=timedelta(seconds=30),
    )

    hass.data[DOMAIN][entry.entry_id] = {
        PV_API: pv_request,
        PV_ROOMS: rooms,
        PV_ROOM_DATA: room_data,
        PV_SCENES: scenes,
        PV_SCENE_DATA: scene_data,
        PV_SHADES: shades,
        PV_SHADE_DATA: shade_data,
        COORDINATOR: coordinator,
    }

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


def map_data_by_id(data):
    """Return a dict with the key being the id for a list of entries."""
    return {entry[ATTR_ID]: entry for entry in data if ATTR_ID in entry}


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
