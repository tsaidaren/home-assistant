"""Config flow for Griddy Power integration."""
import logging

import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.helpers import aiohttp_client
import homeassistant.helpers.config_validation as cv

from . import AsyncGriddy
from .const import CONF_MEMBER_ID, CONF_METER_ID, CONF_SETTLEMENT_POINT, DOMAIN

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MEMBER_ID): cv.positive_int,
        vol.Required(CONF_METER_ID): cv.positive_int,
        vol.Required(CONF_SETTLEMENT_POINT): cv.string,
    }
)


class GriddyGateway:
    """Placeholder class to make tests pass.

    TODO Remove this placeholder class and replace with things from your PyPI package.
    """

    def __init__(self, hass, member_id, meter_id, settlement_point):
        """Initialize."""
        self._member_id = member_id
        self._meter_id = meter_id
        self._settlement_point = settlement_point
        self._websession = aiohttp_client.async_get_clientsession(hass)

    async def authenticate(self) -> bool:
        """Test if we can authenticate with the host."""
        data = await AsyncGriddy(
            self._websession,
            member_id=self._member_id,
            meter_id=self._meter_id,
            settlement_point=self._settlement_point,
        ).async_getnow()
        import pprint

        _LOGGER.debug("authenticate: %s", pprint.pformat(data))

        return True


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    # TODO validate the data can be used to set up a connection.

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func, data["username"], data["password"]
    # )

    gateway = GriddyGateway(
        hass, data[CONF_MEMBER_ID], data[CONF_METER_ID], data[CONF_SETTLEMENT_POINT]
    )

    if not await gateway.authenticate():
        raise InvalidAuth

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    # Return info that you want to store in the config entry.
    return {"title": f"Meter {data[CONF_METER_ID]}"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Griddy Power."""

    VERSION = 1
    # TODO pick one of the available connection classes in homeassistant/config_entries.py
    CONNECTION_CLASS = config_entries.CONN_CLASS_UNKNOWN

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)

                return self.async_create_entry(title=info["title"], data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
