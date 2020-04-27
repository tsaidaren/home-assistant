"""Support for hunter douglas shades."""
import logging

from aiopvapi.helpers.constants import ATTR_POSITION1, ATTR_POSITION_DATA
from aiopvapi.resources.shade import MAX_POSITION, MIN_POSITION, factory as PvShade

from homeassistant.components.cover import (
    ATTR_POSITION,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_SET_POSITION,
    SUPPORT_STOP,
    CoverEntity,
)
from homeassistant.core import callback

from .const import (
    COORDINATOR,
    DEVICE_INFO,
    DEVICE_MODEL,
    DOMAIN,
    PV_API,
    PV_ROOM_DATA,
    PV_SHADE_DATA,
    ROOM_ID_IN_SHADE,
    ROOM_NAME,
    STATE_ATTRIBUTE_ROOM_NAME,
)
from .entity import HDEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Lutron shades."""

    pv_data = hass.data[DOMAIN][entry.entry_id]
    room_data = pv_data[PV_ROOM_DATA]
    shade_data = pv_data[PV_SHADE_DATA]
    pv_request = pv_data[PV_API]
    coordinator = pv_data[COORDINATOR]
    device_info = pv_data[DEVICE_INFO]

    pvshades = (
        PowerViewShade(
            PvShade(raw_shade, pv_request), room_data, coordinator, device_info
        )
        for shade_id, raw_shade in shade_data.items()
    )
    async_add_entities(pvshades)


def hd_position_to_hass(hd_position):
    """Convert hunter douglas position to hass position."""
    return round((hd_position / 65535) * 100)


def hass_position_to_hd(hass_positon):
    """Convert hass position to hunter douglas position."""
    return int(hass_positon / 100 * 65535)


class PowerViewShade(HDEntity, CoverEntity):
    """Representation of a powerview shade."""

    def __init__(self, shade, room_data, coordinator, device_info):
        """Initialize the shade."""
        super().__init__(coordinator, device_info, shade.id)
        self._shade = shade
        self._device_info = device_info
        self._room_name = None
        room_id = shade.raw_data.get(ROOM_ID_IN_SHADE)
        self._room_name = room_data.get(room_id, {}).get(ROOM_NAME, "")
        self._current_cover_position = MIN_POSITION
        self._coordinator = coordinator

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {STATE_ATTRIBUTE_ROOM_NAME: self._room_name}

    @property
    def supported_features(self):
        """Flag supported features."""
        supported_features = SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_SET_POSITION
        if self._device_info[DEVICE_MODEL] != "1":
            supported_features |= SUPPORT_STOP
        return supported_features

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        return self._current_cover_position == MIN_POSITION

    @property
    def current_cover_position(self):
        """Return the current position of cover."""
        return hd_position_to_hass(self._current_cover_position)

    @property
    def name(self):
        """Return the name of the shade."""
        return self._shade.name

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        await self._shade.close()
        self._current_cover_position = MIN_POSITION
        self.async_write_ha_state()

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        await self._shade.open()
        self._current_cover_position = MAX_POSITION
        self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        await self._shade.stop()
        await self._shade.refresh()
        self.async_write_ha_state()

    async def set_cover_position(self, **kwargs):
        """Move the shade to a specific position."""
        if ATTR_POSITION in kwargs:
            position = kwargs[ATTR_POSITION]
            await self._shade.move(hass_position_to_hd(position))

    @callback
    def _async_update_shade(self):
        """Update with new data from the coordinator."""
        self._shade.raw_data = self._coordinator.data[self._shade.id]
        self.async_write_ha_state()

    @callback
    def _async_update_current_cover_position(self):
        """Update the current cover position from the data."""
        position_data = self._shade.raw_data[ATTR_POSITION_DATA]
        if ATTR_POSITION1 in position_data:
            self._current_cover_position = position_data[ATTR_POSITION1]

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self._async_update_current_cover_position()
        self.async_on_remove(
            self._coordinator.async_add_listener(self._async_update_shade)
        )
