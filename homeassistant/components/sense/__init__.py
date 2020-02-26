"""Support for monitoring a Sense energy sensor."""
import asyncio
from datetime import timedelta
import logging

from sense_energy import (
    ASyncSenseable,
    SenseAPITimeoutException,
    SenseAuthenticationException,
)
import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_TIMEOUT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later
import homeassistant.util.dt as dt_util

from .const import (
    ACTIVE_UPDATE_RATE,
    DEFAULT_TIMEOUT,
    DOMAIN,
    SENSE_DATA,
    SENSE_DEVICE_UPDATE,
    SENSE_DEVICES_DATA,
    SENSE_WEBSOCKET,
)

MIN_EXPECTED_DATA_INTERVAL = timedelta(seconds=DEFAULT_TIMEOUT)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor"]

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_EMAIL): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


class SenseDevicesData:
    def __init__(self):
        self._data_by_device = {}

    def set_device_data(self, devices):
        """Store a device update."""
        for device in devices:
            self._data_by_device[device["id"]] = device

    def get_device_data(self, sense_device_id):
        """Get the latest device data."""
        return self._data_by_device.get(sense_device_id)


class SenseWebSocket:
    """The sense websocket."""

    def __init__(self, hass, gateway, sense_devices_data):
        """Create the sense websocket."""
        self._gateway = gateway
        self._hass = hass
        self._watchdog_listener = None
        self._async_realtime_stream = None
        self._sense_devices_data = sense_devices_data
        self._last_activity = dt_util.utcnow()

    async def start(self):
        """Start the sense websocket."""
        if self._async_realtime_stream is not None:
            await self.stop()

        _LOGGER.debug("start websocket")
        self._async_realtime_stream = asyncio.create_task(
            self._gateway.async_realtime_stream(callback=self._on_realtime_update)
        )
        self._async_reset_watchdog()

    async def stop(self):
        """Stop the sense websocket."""
        if self._async_realtime_stream is not None:
            return
        if self._watchdog_listener is not None:
            self._watchdog_listener()

        self._async_realtime_stream.cancel()

        try:
            self._async_realtime_stream.result()
        except SenseAPITimeoutException:
            _LOGGER.error("Websocket timed out retrieving data.")

        self._async_realtime_stream = None

    def _async_reset_watchdog(self):
        self._watchdog_listener = async_call_later(
            self._hass, DEFAULT_TIMEOUT, self._restart_websocket_or_reset_watchdog
        )

    async def _restart_websocket_or_reset_watchdog(self, time):
        if dt_util.utcnow() - self._last_activity < MIN_EXPECTED_DATA_INTERVAL:
            self._async_reset_watchdog()
            return

        await self.stop()
        await self.start()

    def _on_realtime_update(self, data):
        self._last_activity = dt_util.utcnow()

        if "devices" in data:
            self._sense_devices_data.set_device_data(data["devices"])

        async_dispatcher_send(
            self._hass, f"{SENSE_DEVICE_UPDATE}-{self._gateway.sense_monitor_id}"
        )


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Sense component."""
    hass.data.setdefault(DOMAIN, {})
    conf = config.get(DOMAIN)
    if not conf:
        return True

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={CONF_EMAIL: conf[CONF_EMAIL], CONF_PASSWORD: conf[CONF_PASSWORD]},
        )
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Sense from a config entry."""

    entry_data = entry.data
    email = entry_data[CONF_EMAIL]
    password = entry_data[CONF_PASSWORD]

    gateway = ASyncSenseable(api_timeout=DEFAULT_TIMEOUT, wss_timeout=DEFAULT_TIMEOUT)

    try:
        await gateway.authenticate(email, password)
    except SenseAuthenticationException:
        _LOGGER.error("Could not authenticate with sense server")
        return False
    except SenseAPITimeoutException:
        raise ConfigEntryNotReady

    sense_devices_data = SenseDevicesData()
    sense_websocket = SenseWebSocket(hass, gateway, sense_devices_data)

    hass.data[DOMAIN][entry.entry_id] = {
        SENSE_DATA: gateway,
        SENSE_WEBSOCKET: sense_websocket,
        SENSE_DEVICES_DATA: sense_devices_data,
    }

    await sense_websocket.start()

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


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

    await hass.data[DOMAIN][entry.entry_id][SENSE_WEBSOCKET].stop()

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
