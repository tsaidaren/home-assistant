"""Config flow for Universal Devices ISY994 integration."""
import logging
from urllib.parse import urlparse

from pyisy import ISY
import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.components.binary_sensor import (
    DEVICE_CLASSES_SCHEMA as BINARY_SENSOR_DCS,
)
from homeassistant.components.sensor import DEVICE_CLASSES_SCHEMA as SENSOR_DCS
from homeassistant.const import (
    CONF_BINARY_SENSORS,
    CONF_DEVICE_CLASS,
    CONF_HOST,
    CONF_ICON,
    CONF_ID,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PAYLOAD_OFF,
    CONF_PAYLOAD_ON,
    CONF_SENSORS,
    CONF_SWITCHES,
    CONF_TYPE,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_USERNAME,
)

from .const import (
    CONF_ENABLE_CLIMATE,
    CONF_IGNORE_STRING,
    CONF_ISY_VARIABLES,
    CONF_SENSOR_STRING,
    CONF_TLS_VER,
    DEFAULT_IGNORE_STRING,
    DEFAULT_OFF_VALUE,
    DEFAULT_ON_VALUE,
    DEFAULT_SENSOR_STRING,
)
from .const import DOMAIN  # pylint:disable=unused-import

_LOGGER = logging.getLogger(__name__)


VAR_BASE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ID): int,
        vol.Required(CONF_TYPE): vol.All(int, vol.In([1, 2])),
        vol.Optional(CONF_ICON): str,
        vol.Optional(CONF_NAME): str,
    }
)

SENSOR_VAR_SCHEMA = VAR_BASE_SCHEMA.extend(
    {
        vol.Optional(CONF_DEVICE_CLASS): SENSOR_DCS,
        vol.Optional(CONF_UNIT_OF_MEASUREMENT): str,
    }
)

BINARY_SENSOR_VAR_SCHEMA = VAR_BASE_SCHEMA.extend(
    {
        vol.Optional(CONF_DEVICE_CLASS): BINARY_SENSOR_DCS,
        vol.Optional(CONF_PAYLOAD_ON, default=DEFAULT_ON_VALUE): vol.Coerce(int),
        vol.Optional(CONF_PAYLOAD_OFF, default=DEFAULT_OFF_VALUE): vol.Coerce(int),
    }
)

SWITCH_VAR_SCHEMA = VAR_BASE_SCHEMA.extend(
    {
        vol.Optional(CONF_PAYLOAD_ON, default=DEFAULT_ON_VALUE): vol.Coerce(int),
        vol.Optional(CONF_PAYLOAD_OFF, default=DEFAULT_OFF_VALUE): vol.Coerce(int),
    }
)

ISY_VARIABLES_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_SENSORS, default=[]): vol.All(list, [SENSOR_VAR_SCHEMA]),
        vol.Optional(CONF_BINARY_SENSORS, default=[]): vol.All(
            list, [BINARY_SENSOR_VAR_SCHEMA]
        ),
        vol.Optional(CONF_SWITCHES, default=[]): vol.All(list, [SWITCH_VAR_SCHEMA]),
    }
)


DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_TLS_VER): vol.Coerce(float),
        vol.Optional(CONF_IGNORE_STRING, default=DEFAULT_IGNORE_STRING): str,
        vol.Optional(CONF_SENSOR_STRING, default=DEFAULT_SENSOR_STRING): str,
        vol.Optional(CONF_ENABLE_CLIMATE, default=True): bool,
        vol.Optional(CONF_ISY_VARIABLES, default={}): ISY_VARIABLES_SCHEMA,
    }
)


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    user = data[CONF_USERNAME]
    password = data[CONF_PASSWORD]
    host = urlparse(data[CONF_HOST])
    tls_version = data.get(CONF_TLS_VER)

    if host.scheme == "http":
        https = False
        port = host.port or 80
    elif host.scheme == "https":
        https = True
        port = host.port or 443
    else:
        _LOGGER.error("isy994 host value in configuration is invalid")
        return False

    # Connect to ISY controller.
    isy = ISY(
        host.hostname,
        port,
        username=user,
        password=password,
        use_https=https,
        tls_ver=tls_version,
        log=_LOGGER,
    )
    if not isy.connected:
        raise InvalidAuth

    # Return info that you want to store in the config entry.
    return {"title": host.hostname}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Universal Devices ISY994."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

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

    async def async_step_import(self, user_input):
        """Handle import."""
        await self.async_set_unique_id(user_input[CONF_HOST])
        self._abort_if_unique_id_configured()

        return await self.async_step_user(user_input)


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
