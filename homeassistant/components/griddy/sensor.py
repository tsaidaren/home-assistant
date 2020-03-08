"""Support for August sensors."""
import logging

# from homeassistant.components.sensor import DEVICE_CLASS_POWER
from homeassistant.helpers.entity import Entity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the August sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    import pprint

    _LOGGER.debug("GIRDDY: %s", pprint.pformat(coordinator.data))
    #    coordinator.data
    devices = []
    devices.append(GriddyPriceSensor(coordinator))

    async_add_entities(devices, True)


class GriddyPriceSensor(Entity):
    """Representation of an August sensor."""

    def __init__(self, coordinator):
        """Initialize the sensor."""
        self._coordinator = coordinator
        self._update_from_data()
