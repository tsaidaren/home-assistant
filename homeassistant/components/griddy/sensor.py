"""Support for August sensors."""
import logging

from homeassistant.components.sensor import DEVICE_CLASS_POWER
from homeassistant.helpers.entity import Entity

from .const import CONF_MEMBER_ID, CONF_METER_ID, CONF_SETTLEMENT_POINT, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the August sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    meter_id = config_entry.data[CONF_METER_ID]
    member_id = config_entry.data[CONF_MEMBER_ID]
    settlement_point = config_entry.data[CONF_SETTLEMENT_POINT]

    import pprint

    _LOGGER.debug("GIRDDY: %s", pprint.pformat(coordinator.data))
    #    coordinator.data
    devices = []
    devices.append(
        GriddyPriceSensor(meter_id, member_id, settlement_point, coordinator)
    )

    async_add_entities(devices, True)


class GriddyPriceSensor(Entity):
    """Representation of an August sensor."""

    def __init__(self, meter_id, member_id, settlement_point, coordinator):
        """Initialize the sensor."""
        self._coordinator = coordinator
        self._member_id = member_id
        self._meter_id = meter_id
        self._settlement_point = settlement_point
        self._update_from_data()

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "¢/kwh"

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return DEVICE_CLASS_POWER

    def name(self):
        """Device Name."""
        return f"{self._meter_id} Price Now"

    def unique_id(self):
        """Device Uniqueid."""
        return f"{self._meter_id} price now"

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        return {"load zone": self._settlement_point}

    @property
    def available(self):
        """Return True if entity is available."""
        return self._coordinator.last_update_success

    @property
    def state(self):
        """Get the current price."""
        return round(float(self._coordinator.data["now"]["price_ckwh"]), 4)

    @property
    def should_poll(self):
        """Return False, updates are controlled via coordinator."""
        return False

    async def async_update(self):
        await self._coordinator.async_request_refresh()

    async def async_added_to_hass(self):
        """Subscribe to updates."""
        self._coordinator.async_add_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        """Undo subscription."""
        self._coordinator.async_remove_listener(self.async_write_ha_state)
