"""Support for August sensors."""
import logging

from homeassistant.const import DEVICE_CLASS_POWER
from homeassistant.helpers.entity import Entity

from .const import (
    DOMAIN,
    POWERWALL_API_GRID_STATUS,
    POWERWALL_API_SITEMASTER,
    POWERWALL_COORDINATOR,
    POWERWALL_GRID_ONLINE,
    POWERWALL_IP_ADDRESS,
    POWERWALL_RUNNING_KEY,
    POWERWALL_SITE_INFO,
    POWERWALL_SITE_NAME,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the August sensors."""
    powerwall_data = hass.data[DOMAIN][config_entry.entry_id]

    coordinator = powerwall_data[POWERWALL_COORDINATOR]
    site_info = powerwall_data[POWERWALL_SITE_INFO]
    ip_address = powerwall_data[POWERWALL_IP_ADDRESS]

    entities = []
    entities.append(PowerWallRunningSensor(coordinator, site_info, ip_address))
    entities.append(PowerWallGridStatusSensor(coordinator, site_info, ip_address))

    async_add_entities(entities, True)


class PowerWallBinarySensor(Entity):
    """Base class for powerwall binary sensors."""

    def __init__(self, coordinator):
        """Initialize the sensor."""
        self._coordinator = coordinator

    @property
    def available(self):
        """Return True if entity is available."""
        return self._coordinator.last_update_success

    @property
    def should_poll(self):
        """Return False, updates are controlled via coordinator."""
        return False

    async def async_update(self):
        """Update the entity.

        Only used by the generic entity update service.
        """
        await self._coordinator.async_request_refresh()

    async def async_added_to_hass(self):
        """Subscribe to updates."""
        self._coordinator.async_add_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        """Undo subscription."""
        self._coordinator.async_remove_listener(self.async_write_ha_state)


class PowerWallRunningSensor(PowerWallBinarySensor):
    """Representation of an Powerwall running sensor."""

    def __init__(self, coordinator, site_info, ip_address):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._site_info = site_info
        self._site_name = site_info[POWERWALL_SITE_NAME]
        self._ip_address = ip_address

    @property
    def name(self):
        """Device Name."""
        return f"{self._site_name} Powerwall Status"

    @property
    def device_class(self):
        """Device Class."""
        return DEVICE_CLASS_POWER

    @property
    def unique_id(self):
        """Device Uniqueid."""
        return f"{self._ip_address}_running"

    @property
    def state(self):
        """Get the powerwall running state."""
        return self._coordinator.data[POWERWALL_API_SITEMASTER][POWERWALL_RUNNING_KEY]


class PowerWallGridStatusSensor(PowerWallBinarySensor):
    """Representation of an Powerwall Energy sensor."""

    def __init__(self, coordinator, site_info, ip_address):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._site_info = site_info
        self._site_name = site_info[POWERWALL_SITE_NAME]
        self._ip_address = ip_address

    @property
    def name(self):
        """Device Name."""
        return f"{self._site_name} Grid Status"

    @property
    def device_class(self):
        """Device Class."""
        return DEVICE_CLASS_POWER

    @property
    def unique_id(self):
        """Device Uniqueid."""
        return f"{self._ip_address}_grid_status"

    @property
    def state(self):
        """Get the current value in kWh."""
        return (
            self._coordinator.data[POWERWALL_API_GRID_STATUS] == POWERWALL_GRID_ONLINE
        )
