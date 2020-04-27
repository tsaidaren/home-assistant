"""Support for hunter douglas shades."""
import logging

from aiopvapi.helpers.constants import ATTR_POSITION1, ATTR_POSITION_DATA
from aiopvapi.resources.shade import (
    ATTR_POSKIND1,
    ATTR_TYPE,
    MAX_POSITION,
    MIN_POSITION,
    factory as PvShade,
)

from homeassistant.components.cover import (
    ATTR_POSITION,
    DEVICE_CLASS_SHADE,
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
    DEVICE_SERIAL_NUMBER,
    DOMAIN,
    FIRMWARE_BUILD,
    FIRMWARE_IN_SHADE,
    FIRMWARE_REVISION,
    FIRMWARE_SUB_REVISION,
    MANUFACTURER,
    PV_API,
    PV_ROOM_DATA,
    PV_SHADE_DATA,
    ROOM_ID_IN_SHADE,
    ROOM_NAME,
    SHADE_RESPONSE,
    STATE_ATTRIBUTE_ROOM_NAME,
)
from .entity import HDEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the hunter douglas shades."""

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
    return round((hd_position / MAX_POSITION) * 100)


def hass_position_to_hd(hass_positon):
    """Convert hass position to hunter douglas position."""
    return int(hass_positon / 100 * MAX_POSITION)


class PowerViewShade(HDEntity, CoverEntity):
    """Representation of a powerview shade."""

    def __init__(self, shade, room_data, coordinator, device_info):
        """Initialize the shade."""
        room_id = shade.raw_data.get(ROOM_ID_IN_SHADE)
        super().__init__(coordinator, device_info, shade.id)
        self._shade = shade
        self._device_info = device_info
        self._is_opening = False
        self._is_closing = False
        self._room_name = None
        self._name = self._shade.name
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
    def is_opening(self):
        """Return if the cover is opening."""
        return self._is_opening

    @property
    def is_closing(self):
        """Return if the cover is closing."""
        return self._is_closing

    @property
    def current_cover_position(self):
        """Return the current position of cover."""
        return hd_position_to_hass(self._current_cover_position)

    @property
    def device_class(self):
        """Return device class."""
        return DEVICE_CLASS_SHADE

    @property
    def name(self):
        """Return the name of the shade."""
        return self._name

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        await self._async_move(0)
        self._is_closing = True
        self.async_write_ha_state()

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        await self._async_move(100)
        self._is_opening = True
        self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        self._async_update_from_command(await self._shade.stop())
        self.async_write_ha_state()

    async def set_cover_position(self, **kwargs):
        """Move the shade to a specific position."""
        if ATTR_POSITION not in kwargs:
            return
        await self._async_move(kwargs[ATTR_POSITION])

    async def _async_move(self, hass_position):
        """Move the shade to a position."""
        self._async_update_from_command(
            await self._shade.move(
                {ATTR_POSITION1: hass_position_to_hd(hass_position), ATTR_POSKIND1: 1}
            )
        )

    @callback
    def _async_update_from_command(self, raw_data):
        """Update the shade state after a command."""
        if not raw_data or SHADE_RESPONSE not in raw_data:
            return
        self._async_process_new_shade_data(raw_data[SHADE_RESPONSE])

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self._async_update_current_cover_position()
        self.async_on_remove(
            self._coordinator.async_add_listener(self._async_update_shade)
        )

    @callback
    def _async_update_shade(self):
        """Update with new data from the coordinator."""
        self._async_process_new_shade_data(self._coordinator.data[self._shade.id])
        self.async_write_ha_state()

    @callback
    def _async_process_new_shade_data(self, data):
        """Process new data from an update."""
        self._shade.raw_data = data
        self._async_update_current_cover_position()

    @callback
    def _async_update_current_cover_position(self):
        """Update the current cover position from the data."""
        _LOGGER.debug("Raw data update: %s", self._shade.raw_data)
        position_data = self._shade.raw_data[ATTR_POSITION_DATA]
        if ATTR_POSITION1 in position_data:
            self._current_cover_position = position_data[ATTR_POSITION1]
        self._is_opening = False
        self._is_closing = False

    @property
    def device_info(self):
        """Return the device_info of the device."""
        firmware = self._shade.raw_data[FIRMWARE_IN_SHADE]
        sw_version = f"{firmware[FIRMWARE_REVISION]}.{firmware[FIRMWARE_SUB_REVISION]}.{firmware[FIRMWARE_BUILD]}"
        model = self._shade.raw_data[ATTR_TYPE]
        for shade in self._shade.shade_types:
            if shade.shade_type == model:
                model = shade.description
                break

        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "model": str(model),
            "sw_version": sw_version,
            "manufacturer": MANUFACTURER,
            "via_device": (DOMAIN, self._device_info[DEVICE_SERIAL_NUMBER]),
        }
