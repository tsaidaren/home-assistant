"""Common code for tplink."""
import asyncio
from datetime import timedelta
import logging
from typing import Any, Awaitable, Callable, List

from kasa import (
    Discover,
    SmartBulb,
    SmartDevice,
    SmartDeviceException,
    SmartDimmer,
    SmartPlug,
    SmartStrip,
)

from homeassistant.helpers.typing import HomeAssistantType

_LOGGER = logging.getLogger(__name__)


ATTR_CONFIG = "config"
CONF_DIMMER = "dimmer"
CONF_DISCOVERY = "discovery"
CONF_LIGHT = "light"
CONF_STRIP = "strip"
CONF_SWITCH = "switch"


class SmartDevices:
    """Hold different kinds of devices."""

    def __init__(
        self, lights: List[SmartDevice] = None, switches: List[SmartDevice] = None
    ):
        """Initialize device holder."""
        self._lights = lights or []
        self._switches = switches or []

    @property
    def lights(self):
        """Get the lights."""
        return self._lights

    @property
    def switches(self):
        """Get the switches."""
        return self._switches

    def has_device_with_host(self, host):
        """Check if a devices exists with a specific host."""
        for device in self.lights + self.switches:
            if device.host == host:
                return True

        return False


async def async_get_discoverable_devices(hass):
    """Return if there are devices that can be discovered."""
    return await Discover.discover()


async def async_discover_devices(
    hass: HomeAssistantType, existing_devices: SmartDevices
) -> SmartDevices:
    """Get devices through discovery."""
    _LOGGER.debug("Discovering devices")
    devices = await async_get_discoverable_devices(hass)
    _LOGGER.info("Discovered %s TP-Link smart home device(s)", len(devices))

    lights = []
    switches = []

    for dev in devices.values():
        await dev.update()
        # If this device already exists, ignore dynamic setup.
        if existing_devices.has_device_with_host(dev.host):
            continue

        if dev.is_strip or dev.is_plug:
            switches.append(dev)
        elif dev.is_dimmer or dev.is_bulb:
            lights.append(dev)
        else:
            _LOGGER.error("Unknown smart device type: %s", dev.device_type)

    return SmartDevices(lights, switches)


def get_static_devices(config_data) -> SmartDevices:
    """Get statically defined devices in the config."""
    _LOGGER.debug("Getting static devices")
    lights = []
    switches = []

    for type_ in [CONF_LIGHT, CONF_SWITCH, CONF_STRIP, CONF_DIMMER]:
        for entry in config_data[type_]:
            host = entry["host"]

            if type_ == CONF_LIGHT:
                lights.append(SmartBulb(host))
            elif type_ == CONF_SWITCH:
                switches.append(SmartPlug(host))
            elif type_ == CONF_STRIP:
                switches.append(SmartStrip(host))
            elif type_ == CONF_DIMMER:
                lights.append(SmartDimmer(host))

    return SmartDevices(lights, switches)


AsyncAddEntities = Callable[[List[Any], bool], None]
AddEntitiesCallable = Callable[[Any, AsyncAddEntities], Awaitable[bool]]


async def async_add_entities_retry(
    hass: HomeAssistantType,
    async_add_entities: AsyncAddEntities,
    objects: List[Any],
    callback: AddEntitiesCallable,
    interval: timedelta = timedelta(seconds=60),
):
    """
    Add entities now and retry later if issues are encountered.

    If the callback throws an exception or returns false, that
    object will try again a while later.
    This is useful for devices that are not online when hass starts.
    :param hass:
    :param async_add_entities: The callback provided to a
    platform's async_setup.
    :param objects: The objects to create as entities.
    :param callback: The callback that will perform the add.
    :param interval: THe time between attempts to add.
    :return: A callback to cancel the retries.
    """
    add_objects = objects.copy()

    is_cancelled = False

    def cancel_interval_callback():
        nonlocal is_cancelled
        is_cancelled = True

    async def process_objects_loop(delay: int):
        if is_cancelled:
            return

        await process_objects()

        if not add_objects:
            return

        await asyncio.sleep(delay)

        hass.async_create_task(process_objects_loop(delay))

    async def process_objects(*args):
        # Process each object.
        for add_object in list(add_objects):
            # Call the individual item callback.
            try:
                _LOGGER.debug("Attempting to add object of type %s", type(add_object))
                result = await callback(add_object, async_add_entities)
            except SmartDeviceException as ex:
                _LOGGER.debug(str(ex))
                result = False

            if result is True or result is None:
                _LOGGER.debug("Added object.")
                add_objects.remove(add_object)
            else:
                _LOGGER.debug("Failed to add object, will try again later")

    await process_objects_loop(interval.seconds)

    return cancel_interval_callback
