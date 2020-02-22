"""Support for August sensors."""
import logging

from homeassistant.components.sensor import DEVICE_CLASS_BATTERY
from homeassistant.helpers.entity import Entity

from . import DATA_AUGUST, MIN_TIME_BETWEEN_DETAIL_UPDATES

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = MIN_TIME_BETWEEN_DETAIL_UPDATES


async def _async_retrieve_battery_state(data, doorbell):
    """Get the latest state of the sensor."""
    detail = await data.async_get_doorbell_detail(doorbell.device_id)
    import pprint

    pprint.pprint(detail)
    pprint.pprint(detail.battery_level)
    if detail is None:
        return None

    return detail.battery_level


SENSOR_NAME = 0
SENSOR_DEVICE_CLASS = 1
SENSOR_STATE_PROVIDER = 2
SENSOR_UNIT_OF_MEASUREMENT = 3

# sensor_type: [name, device_class, async_state_provider, unit_of_measurement]
SENSOR_TYPES_DOORBELL = {
    "doorbell_battery": [
        "Battery",
        DEVICE_CLASS_BATTERY,
        _async_retrieve_battery_state,
        "%",
    ],
}


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the August sensors."""
    data = hass.data[DATA_AUGUST]
    devices = []

    for doorbell in data.doorbells:
        for sensor_type in SENSOR_TYPES_DOORBELL:
            _LOGGER.debug(
                "Adding doorbell sensor class %s for %s",
                SENSOR_TYPES_DOORBELL[sensor_type][SENSOR_DEVICE_CLASS],
                doorbell.device_name,
            )
            devices.append(AugustDoorbellSensor(data, sensor_type, doorbell))

    async_add_entities(devices, True)


class AugustDoorbellSensor(Entity):
    """Representation of an August sensor."""

    def __init__(self, data, sensor_type, doorbell):
        """Initialize the sensor."""
        self._data = data
        self._sensor_type = sensor_type
        self._doorbell = doorbell
        self._state = None
        self._available = False

    @property
    def available(self):
        """Return the availability of this sensor."""
        return self._available

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return SENSOR_TYPES_DOORBELL[self._sensor_type][SENSOR_UNIT_OF_MEASUREMENT]

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return SENSOR_TYPES_DOORBELL[self._sensor_type][SENSOR_DEVICE_CLASS]

    @property
    def name(self):
        """Return the name of the sensor."""
        return "{} {}".format(
            self._doorbell.device_name,
            SENSOR_TYPES_DOORBELL[self._sensor_type][SENSOR_NAME],
        )

    async def async_update(self):
        """Get the latest state of the sensor."""
        async_state_provider = SENSOR_TYPES_DOORBELL[self._sensor_type][
            SENSOR_STATE_PROVIDER
        ]
        self._state = await async_state_provider(self._data, self._doorbell)
        # The doorbell will go into standby mode when there is no motion
        # for a short while. It will wake by itself when needed so we need
        # to consider is available or we will not report motion or dings
        self._available = self._doorbell.is_online or self._doorbell.is_standby

    @property
    def unique_id(self) -> str:
        """Get the unique id of the doorbell sensor."""
        return "{:s}_{:s}".format(
            self._doorbell.device_id,
            SENSOR_TYPES_DOORBELL[self._sensor_type][SENSOR_NAME].lower(),
        )
