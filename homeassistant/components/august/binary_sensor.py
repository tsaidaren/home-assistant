"""Support for August binary sensors."""
from datetime import datetime, timedelta
import logging

from august.activity import ActivityType
from august.lock import LockDoorStatus
from august.util import update_lock_detail_from_activity

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_CONNECTIVITY,
    DEVICE_CLASS_MOTION,
    DEVICE_CLASS_OCCUPANCY,
    BinarySensorDevice,
)

from . import DEFAULT_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=5)


async def _async_retrieve_online_state(data, doorbell, detail):
    """Get the latest state of the sensor."""
    if detail is None:
        return None

    return detail.is_online or detail.is_standby


async def _async_retrieve_motion_state(data, doorbell, detail):

    return await _async_activity_time_based_state(
        data, doorbell, [ActivityType.DOORBELL_MOTION, ActivityType.DOORBELL_DING]
    )


async def _async_retrieve_ding_state(data, doorbell, detail):

    return await _async_activity_time_based_state(
        data, doorbell, [ActivityType.DOORBELL_DING]
    )


async def _async_activity_time_based_state(data, doorbell, activity_types):
    """Get the latest state of the sensor."""
    latest = await data.async_get_latest_device_activity(
        doorbell.device_id, *activity_types
    )

    if latest is not None:
        start = latest.activity_start_time
        end = latest.activity_end_time + timedelta(seconds=45)
        return start <= datetime.now() <= end
    return None


SENSOR_NAME = 0
SENSOR_DEVICE_CLASS = 1
SENSOR_STATE_PROVIDER = 2

# sensor_type: [name, device_class, async_state_provider]
SENSOR_TYPES_DOORBELL = {
    "doorbell_ding": ["Ding", DEVICE_CLASS_OCCUPANCY, _async_retrieve_ding_state],
    "doorbell_motion": ["Motion", DEVICE_CLASS_MOTION, _async_retrieve_motion_state],
    "doorbell_online": [
        "Online",
        DEVICE_CLASS_CONNECTIVITY,
        _async_retrieve_online_state,
    ],
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the August binary sensors."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    devices = []

    for door in data.locks:
        if not data.lock_has_doorsense(door.device_id):
            _LOGGER.debug(
                "Not adding sensor class door for lock %s ", door.device_name,
            )
            continue

        _LOGGER.debug(
            "Adding sensor class door for %s", door.device_name,
        )
        devices.append(AugustDoorBinarySensor(data, "door_open", door))

    for doorbell in data.doorbells:
        for sensor_type in SENSOR_TYPES_DOORBELL:
            _LOGGER.debug(
                "Adding doorbell sensor class %s for %s",
                SENSOR_TYPES_DOORBELL[sensor_type][SENSOR_DEVICE_CLASS],
                doorbell.device_name,
            )
            devices.append(AugustDoorbellBinarySensor(data, sensor_type, doorbell))

    async_add_entities(devices, True)


class AugustBinarySensor(BinarySensorDevice):
    """Representation of an August binary sensor."""

    @property
    def available(self):
        """Return the availability of this sensor."""
        return self._available

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._state


class AugustDoorBinarySensor(AugustBinarySensor):
    """Representation of an August Door binary sensor."""

    def __init__(self, data, sensor_type, door):
        """Initialize the sensor."""
        self._data = data
        self._sensor_type = sensor_type
        self._door = door
        self._state = None
        self._available = False
        self._model = None
        self._firmware_version = None

    @property
    def device_class(self):
        """Return the class of this device."""
        return "door"

    @property
    def name(self):
        """Return the name of the binary sensor."""
        return "{} Open".format(self._door.device_name)

    async def async_update(self):
        """Get the latest state of the sensor and update activity."""
        door_activity = await self._data.async_get_latest_device_activity(
            self._door.device_id, ActivityType.DOOR_OPERATION
        )
        detail = await self._data.async_get_lock_detail(self._door.device_id)

        if door_activity is not None:
            update_lock_detail_from_activity(detail, door_activity)

        lock_door_state = None
        self._available = False
        if detail is not None:
            lock_door_state = detail.door_state
            self._firmware_version = detail.firmware_version
            self._model = detail.model
            self._available = detail.bridge_is_online

        self._state = lock_door_state == LockDoorStatus.OPEN

    @property
    def unique_id(self) -> str:
        """Get the unique of the door open binary sensor."""
        return f"{self._door.device_id}_open"

    @property
    def device_info(self):
        """Return the device_info of the device."""
        return {
            "identifiers": {(DOMAIN, self._door.device_id)},
            "name": self._door.device_name,
            "manufacturer": DEFAULT_NAME,
            "model": self._model,
            "sw_version": self._firmware_version,
        }


class AugustDoorbellBinarySensor(AugustBinarySensor):
    """Representation of an August binary sensor."""

    def __init__(self, data, sensor_type, doorbell):
        """Initialize the sensor."""
        self._data = data
        self._sensor_type = sensor_type
        self._doorbell = doorbell
        self._state = None
        self._available = False
        self._model = None
        self._firmware_version = None

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return SENSOR_TYPES_DOORBELL[self._sensor_type][SENSOR_DEVICE_CLASS]

    @property
    def name(self):
        """Return the name of the binary sensor."""
        return "{} {}".format(
            self._doorbell.device_name,
            SENSOR_TYPES_DOORBELL[self._sensor_type][SENSOR_NAME],
        )

    async def async_update(self):
        """Get the latest state of the sensor."""
        async_state_provider = SENSOR_TYPES_DOORBELL[self._sensor_type][
            SENSOR_STATE_PROVIDER
        ]
        detail = await self._data.async_get_doorbell_detail(self._doorbell.device_id)
        self._state = await async_state_provider(self._data, self._doorbell, detail)
        # The doorbell will go into standby mode when there is no motion
        # for a short while. It will wake by itself when needed so we need
        # to consider is available or we will not report motion or dings
        if self.device_class == DEVICE_CLASS_CONNECTIVITY:
            self._available = True
        else:
            self._available = detail is not None and (
                detail.is_online or detail.is_standby
            )

        if detail is not None:
            self._firmware_version = detail.firmware_version

    @property
    def unique_id(self) -> str:
        """Get the unique id of the doorbell sensor."""
        return "{:s}_{:s}".format(
            self._doorbell.device_id,
            SENSOR_TYPES_DOORBELL[self._sensor_type][SENSOR_NAME].lower(),
        )

    @property
    def device_info(self):
        """Return the device_info of the device."""
        return {
            "identifiers": {(DOMAIN, self._doorbell.device_id)},
            "name": self._doorbell.device_name,
            "manufacturer": "August",
            "model": self._model,
            "sw_version": self._firmware_version,
        }
