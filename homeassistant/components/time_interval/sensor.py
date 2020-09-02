"""Support for time interval sensors."""
import logging

import voluptuous as vol

from homeassistant.components.sensor import DEVICE_CLASS_TIMESTAMP, PLATFORM_SCHEMA
from homeassistant.const import CONF_SENSORS
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.reload import async_setup_reload_service

from . import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)

CONF_HOURS = "hours"
CONF_MINUTES = "minutes"
CONF_SECONDS = "seconds"

SENSOR_SCHEMA = vol.All(
    vol.Schema(
        {
            CONF_HOURS: cv.TimePattern(maximum=23),
            CONF_MINUTES: cv.TimePattern(maximum=59),
            CONF_SECONDS: cv.TimePattern(maximum=59),
        }
    ),
    cv.has_at_least_one_key(CONF_HOURS, CONF_MINUTES, CONF_SECONDS),
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Required(CONF_SENSORS): cv.schema_with_slug_keys(SENSOR_SCHEMA)}
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the time interval sensor."""

    async_setup_reload_service(hass, DOMAIN, PLATFORMS)

    if hass.config.time_zone is None:
        _LOGGER.error("Timezone is not set in Home Assistant configuration")
        return False

    entities = []

    for device, device_config in config[CONF_SENSORS].items():
        entities.append(
            TimeIntervalSensor(
                device,
                device_config.get(CONF_HOURS),
                device_config.get(CONF_MINUTES),
                device_config.get(CONF_SECONDS),
            )
        )

    async_add_entities(entities)


class TimeIntervalSensor(Entity):
    """Implementation of a time interval sensor."""

    def __init__(self, device, hours, minutes, seconds):
        """Initialize the sensor."""
        self._state = None
        self._name = device
        self._hours = hours
        self._minutes = minutes
        self._seconds = seconds

    @property
    def device_class(self):
        """Return the device class."""
        return DEVICE_CLASS_TIMESTAMP

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @callback
    def _async_update(self, now):
        """Update when the time pattern matches."""
        self._state = now
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Set up next update."""
        self.async_on_remove(
            async_track_time_change(
                self.hass,
                self._async_update,
                hour=self._hours,
                minute=self._minutes,
                second=self._seconds,
            )
        )
