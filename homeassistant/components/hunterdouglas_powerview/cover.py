"""Support for hunter douglas shades."""
import logging

from aiopvapi.helpers.constants import (
    ATTR_ID,
    ATTR_NAME,
    ATTR_NAME_UNICODE,
    ATTR_POSITION1,
)
from aiopvapi.resources.shade import factory as PvShade

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
    DOMAIN,
    PV_API,
    PV_ROOM_DATA,
    PV_SHADE_DATA,
    ROOM_NAME,
    SHADE_DATA,
    STATE_ATTRIBUTE_ROOM_NAME,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Lutron shades."""

    pv_data = hass.data[DOMAIN][entry.entry_id]
    room_data = pv_data[PV_ROOM_DATA]
    shade_data = pv_data[PV_SHADE_DATA]
    pv_request = pv_data[PV_API]
    coordinator = pv_data[COORDINATOR]

    pvshades = (
        PowerViewShade(hass, PvShade(raw_shade, pv_request), room_data, coordinator)
        for raw_shade in shade_data[SHADE_DATA]
    )
    async_add_entities(pvshades)


class PowerViewShade(CoverEntity):
    """Representation of a powerview shade."""

    def __init__(self, hass, shade, room_data, coordinator):
        """Initialize the shade."""
        self._shade = shade
        self.hass = hass
        self._room_name = None
        self._room_name = room_data.get(shade.room_id, {}).get(ROOM_NAME, "")
        self._coordinator = coordinator

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {STATE_ATTRIBUTE_ROOM_NAME: self._room_name}

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP | SUPPORT_SET_POSITION

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        return (
            self._shade.get_current_position(refresh=False)
            == self._shade.close_position
        )

    @property
    def current_cover_position(self):
        """Return the current position of cover."""
        # TODO: convert
        return self._shade.get_current_position(refresh=False)

    @property
    def name(self):
        """Return the name of the shade."""
        return self._shade.name

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        await self._shade.close()

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        await self._shade.open()

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        await self._shade.stop()

    async def set_cover_position(self, **kwargs):
        """Move the shade to a specific position."""
        # TODO : convert
        if ATTR_POSITION in kwargs:
            position = kwargs[ATTR_POSITION]
            await self._shade.move(position)

    @callback
    def _async_update_shade(self):
        """Update with new data from the coordinator."""
        self._shade.raw_data = self._coordinator.data[SHADE_DATA][self._shade.id]
        self.async_write_ha_state()

    @property
    def should_poll(self):
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def available(self):
        """Return if entity is available."""
        return self._coordinator.last_update_success

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self._coordinator.async_add_listener(self._async_update_shade)
        )
