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
from aiopvapi.userdata import UserData
import async_timeout
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    COORDINATOR,
    DEVICE_INFO,
    DEVICE_MAC_ADDRESS,
    DEVICE_MODEL,
    DEVICE_NAME,
    DEVICE_REVISION,
    DEVICE_SERIAL_NUMBER,
    DOMAIN,
    FIRMWARE_IN_USERDATA,
    HUB_ADDRESS,
    MAC_ADDRESS_IN_USERDATA,
    MAINPROCESSOR_IN_USERDATA_FIRMWARE,
    MODEL_IN_MAINPROCESSOR,
    PV_API,
    PV_ROOM_DATA,
    PV_SCENE_DATA,
    PV_SHADE_DATA,
    PV_SHADES,
    REVISION_IN_MAINPROCESSOR,
    ROOM_DATA,
    SCENE_DATA,
    SERIAL_NUMBER_IN_USERDATA,
    SHADE_DATA,
    USER_DATA,
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

    async with async_timeout.timeout(10):
        await hub.query_user_data()
    if not hub.ip:
        _LOGGER.error("Unable to initialize PowerView hub: %s", hub_address)
        raise ConfigEntryNotReady

    device_info = await _async_get_device_info(hub, pv_request)

    rooms = Rooms(pv_request)
    room_data = _async_map_data_by_id((await rooms.get_resources())[ROOM_DATA])

    scenes = Scenes(pv_request)
    scene_data = _async_map_data_by_id((await scenes.get_resources())[SCENE_DATA])

    shades = Shades(pv_request)
    shade_data = _async_map_data_by_id((await shades.get_resources())[SHADE_DATA])

    async def async_update_data():
        """Fetch data from shade endpoint."""
        shades = hass.data[DOMAIN][entry.entry_id][PV_SHADES]
        async with async_timeout.timeout(10):
            shade_entries = await shades.get_resources()
        if not shade_entries:
            raise UpdateFailed(f"Failed to fetch new shade data.")
        return _async_map_data_by_id(shade_entries[SHADE_DATA])

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="powerview shades",
        update_method=async_update_data,
        update_interval=timedelta(seconds=30),
    )

    hass.data[DOMAIN][entry.entry_id] = {
        PV_API: pv_request,
        PV_ROOM_DATA: room_data,
        PV_SCENE_DATA: scene_data,
        PV_SHADES: shades,
        PV_SHADE_DATA: shade_data,
        COORDINATOR: coordinator,
        DEVICE_INFO: device_info,
    }

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def _async_get_device_info(hub, pv_request):
    """Determine device info."""
    userdata = UserData(pv_request)
    userdata_data = (await userdata.get_resources())[USER_DATA]
    main_processor_info = userdata_data[FIRMWARE_IN_USERDATA][
        MAINPROCESSOR_IN_USERDATA_FIRMWARE
    ]
    return {
        DEVICE_NAME: hub.name,
        DEVICE_MAC_ADDRESS: userdata_data[MAC_ADDRESS_IN_USERDATA],
        DEVICE_SERIAL_NUMBER: userdata_data[SERIAL_NUMBER_IN_USERDATA],
        DEVICE_REVISION: main_processor_info[REVISION_IN_MAINPROCESSOR],
        DEVICE_MODEL: main_processor_info[MODEL_IN_MAINPROCESSOR],
    }


@callback
def _async_map_data_by_id(data):
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
