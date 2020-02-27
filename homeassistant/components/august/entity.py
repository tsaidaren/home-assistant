"""Base class for August entity."""
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from . import AUGUST_DEVICE_UPDATE, DEFAULT_NAME, DOMAIN


class AugustEntityMixin:
    """Base implementation for August device."""

    def __init__(self, data, device):
        """Initialize an August device."""
        super().__init__()
        self._data = data
        self._device = device
        self._undo_dispatch_subscription = None

    @property
    def ring_objects(self):
        """Return the August API objects."""
        return self.hass.data[DOMAIN][self._config_entry_id]

    @property
    def should_poll(self):
        """Return False, updates are controlled via the hub."""
        return False

    @property
    def _device_id(self):
        self._device.device_id

    @property
    def _detail(self):
        self._data.get_device_detail(self._device.device_id)

    @property
    def device_info(self):
        """Return the device_info of the device."""
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self.name,
            "manufacturer": DEFAULT_NAME,
            "sw_version": self._detail.firmware_version,
            "model": self._detail.model,
        }

    #    async def async_added_to_hass(self):
    #        """Register callbacks."""
    #        self.ring_objects["device_data"].async_add_listener(self._update_callback)
    #
    #    async def async_will_remove_from_hass(self):
    #        """Disconnect callbacks."""
    #        self.ring_objects["device_data"].async_remove_listener(self._update_callback)

    async def async_added_to_hass(self):
        """Register callbacks."""
        self._undo_dispatch_subscription = async_dispatcher_connect(
            self.hass,
            f"{AUGUST_DEVICE_UPDATE}-{self._device_id}",
            self._update_from_data,
        )

    async def async_will_remove_from_hass(self):
        """Undo subscription."""
        if self._undo_dispatch_subscription:
            self._undo_dispatch_subscription()
