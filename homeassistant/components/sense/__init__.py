"""Support for monitoring a Sense energy sensor."""
import asyncio
import logging

from sense_energy import (
    ASyncSenseable,
    SenseAPITimeoutException,
    SenseAuthenticationException,
    SenseWebsocketException,
)
import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_TIMEOUT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later

from .const import (
    ACTIVE_UPDATE_RATE,
    DEFAULT_TIMEOUT,
    DOMAIN,
    SENSE_DATA,
    SENSE_DEVICE_UPDATE,
    SENSE_WEBSOCKET,
)

DEFAULT_WATCHDOG_SECONDS = 5 * 60


_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor"]

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_EMAIL): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


class SenseWebSocket:
    """The sense websocket."""

    def __init__(self, hass, gateway):
        """Create the sense websocket."""
        self._gateway = gateway
        self._hass = hass
        self._watchdog_listener = None
        self._async_realtime_stream = None

    async def start(self):
        """Start the sense websocket."""
        if self._async_realtime_stream is not None:
            await self.stop()

        self._async_realtime_stream = asyncio.create_task(
            self._gateway.async_realtime_stream(callback=self._on_realtime_update)
        )
        await self._async_reset_watchdog()

    async def stop(self):
        """Stop the sense websocket."""
        if self._async_realtime_stream is not None:
            return

        self._async_realtime_stream.cancel()

        try:
            self._async_realtime_stream.result()
        except SenseAPITimeoutException:
            _LOGGER.error("Websocket timed out retrieving data.")
        except SenseWebsocketException as ex:
            _LOGGER.error("Websocket error: %s", ex)

        self._async_realtime_stream = None

    async def _async_reset_watchdog(self):
        if self._watchdog_listener is not None:
            self._watchdog_listener()

        self._watchdog_listener = async_call_later(
            self._hass, DEFAULT_WATCHDOG_SECONDS, self._restart_websocket
        )

    async def _restart_websocket(self):
        await self.stop()
        await self.start()

    def _on_realtime_update(self):
        self._async_reset_watchdog()
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
            data={
                CONF_EMAIL: conf[CONF_EMAIL],
                CONF_PASSWORD: conf[CONF_PASSWORD],
                CONF_TIMEOUT: conf.get[CONF_TIMEOUT],
            },
        )
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Sense from a config entry."""

    entry_data = entry.data
    email = entry_data[CONF_EMAIL]
    password = entry_data[CONF_PASSWORD]
    timeout = entry_data[CONF_TIMEOUT]

    gateway = ASyncSenseable(api_timeout=timeout, wss_timeout=timeout)
    gateway.rate_limit = ACTIVE_UPDATE_RATE

    try:
        await gateway.authenticate(email, password)
    except SenseAuthenticationException:
        _LOGGER.error("Could not authenticate with sense server")
        return False
    except SenseAPITimeoutException:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = {SENSE_DATA: gateway}

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    hass.data[DOMAIN][entry.entry_id][SENSE_WEBSOCKET] = SenseWebSocket(hass, gateway)
    await hass.data[DOMAIN][entry.entry_id][SENSE_WEBSOCKET].start()

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
