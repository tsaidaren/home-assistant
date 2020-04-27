"""The Hunter Douglas PowerView integration."""
import asyncio
from datetime import timedelta
import logging

from aiopvapi.helpers.aiorequest import AioRequest
from aiopvapi.helpers.constants import ATTR_ID
from aiopvapi.hub import Hub
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
    PV_HUB,
    PV_ROOM_DATA,
    PV_SCENE_DATA,
    PV_SHADE_DATA,
    PV_SHADES,
    ROOM_DATA,
    SCENE_DATA,
    SHADE_DATA,
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

    hub = Hub(pv_request)

    async with async_timeout.timeout(20):
        await hub.query_user_data()
        await hub.query_firmware()
    if not hub.ip:
        _LOGGER.error("Unable to initialize PowerView hub: %s", hub_address)
        raise ConfigEntryNotReady

    _LOGGER.debug(
        "Hub: name=%s main_processor_version=%s radio_version=%s",
        hub.name,
        hub.main_processor_version,
        hub.radio_version,
    )

    rooms = Rooms(pv_request)
    room_data = map_data_by_id((await rooms.get_resources())[ROOM_DATA])

    scenes = Scenes(pv_request)
    scene_data = map_data_by_id((await scenes.get_resources())[SCENE_DATA])

    shades = Shades(pv_request)
    shade_data = map_data_by_id((await shades.get_resources())[SHADE_DATA])

    async def async_update_data():
        """Fetch data from shade endpoint."""
        shades = hass.data[DOMAIN][entry.entry_id][PV_SHADES]
        async with async_timeout.timeout(10):
            shade_entries = await shades.get_resources()
        if not shade_entries:
            raise UpdateFailed(f"Failed to fetch new shade data.")
        return map_data_by_id(shade_entries[SHADE_DATA])

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="powerview hub",
        update_method=async_update_data,
        update_interval=timedelta(seconds=30),
    )

    hass.data[DOMAIN][entry.entry_id] = {
        PV_API: pv_request,
        PV_HUB: hub,
        PV_ROOM_DATA: room_data,
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
