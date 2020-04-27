"""The Hunter Douglas PowerView integration."""
import asyncio

from aiopvapi.helpers.aiorequest import AioRequest
from aiopvapi.resources.scene import Scene as PvScene
from aiopvapi.rooms import Rooms
from aiopvapi.scenes import Scenes
from aiopvapi.shades import Shades
import async_timeout
from datatime import timedelta
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity
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
    ROOM_DATA,
    ROOM_ID_IN_SCENE,
    SCENE_DATA,
    SCENE_ID,
    SCENE_NAME,
    STATE_ATTRIBUTE_ROOM_NAME,
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({vol.Required(HUB_ADDRESS): cv.string,})}, extra=vol.ALLOW_EXTRA
)

PLATFORMS = ["cover", "scene"]
_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Hunter Douglas PowerView component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Hunter Douglas PowerView from a config entry."""

    config = entry.data

    hub_address = config.get(HUB_ADDRESS)
    websession = async_get_clientsession(hass)

    pv_request = AioRequest(hub_address, loop=hass.loop, websession=websession)

    rooms = await Rooms(pv_request)
    room_data = await rooms.get_resources()
    if not rooms:
        _LOGGER.error("Unable to initialize PowerView hub: %s", hub_address)
        raise ConfigEntryNotReady

    scenes = Scenes(pv_request)
    scene_data = await scenes.get_resources()
    shades = Shades(pv_request)
    shade_data = await shades.get_resources()

    async def async_update_data():
        """Fetch data from shade endpoint."""
        async with async_timeout.timeout(10):
            shade_data = await hass.data[DOMAIN][entry.entry_id][
                PV_SHADES
            ].get_resources()
        if not shade_data:
            raise UpdateFailed(f"Failed to fetch new shade data.")
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
