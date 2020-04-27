"""Config flow for Hunter Douglas PowerView integration."""
import logging

from aiopvapi.helpers.aiorequest import AioRequest
from aiopvapi.hub import Hub
import async_timeout
import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN  # pylint:disable=unused-import
from .const import HUB_ADDRESS

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({vol.Required(HUB_ADDRESS): str})


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """

    hub_address = data[HUB_ADDRESS]
    websession = async_get_clientsession(hass)

    pv_request = AioRequest(hub_address, loop=hass.loop, websession=websession)
    hub = Hub(pv_request)

    async with async_timeout.timeout(10):
        await hub.query_user_data()
    if not hub.ip:
        raise CannotConnect

    # Return info that you want to store in the config entry.
    return {"title": hub.name}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hunter Douglas PowerView."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            if self._host_already_configured(user_input[HUB_ADDRESS]):
                return self.async_abort(reason="already_configured")
            try:
                info = await validate_input(self.hass, user_input)

                return self.async_create_entry(title=info["title"], data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_import(self, user_input=None):
        """Handle the initial step."""
        return await self.async_step_user(user_input)

    def _host_already_configured(self, host):
        """See if we already have a hub with the host address configured."""
        existing_hosts = {
            entry.data[HUB_ADDRESS] for entry in self._async_current_entries()
        }
        return host in existing_hosts


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""
