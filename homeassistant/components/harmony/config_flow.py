"""Config flow for Logitech Harmony Hub integration."""
import logging
from urllib.parse import urlparse

import aioharmony.exceptions as harmony_exceptions
from aioharmony.harmonyapi import HarmonyAPI
import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.components import ssdp
from homeassistant.components.remote import (
    ATTR_ACTIVITY,
    ATTR_DELAY_SECS,
    DEFAULT_DELAY_SECS,
)
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import callback

from .const import DOMAIN  # pylint:disable=unused-import

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str, vol.Required(CONF_NAME): str})


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    harmony = HarmonyAPI(ip_address=data[CONF_HOST])

    try:
        if not await harmony.connect():
            await harmony.close()
            raise CannotConnect
    except harmony_exceptions.TimeOut:
        raise CannotConnect

    # As a last resort we get the name from the harmony client
    # in the event a name was not provided
    if CONF_NAME not in data or data[CONF_NAME] is None or data[CONF_NAME] == "":
        data[CONF_NAME] = harmony.name

    return {CONF_NAME: data[CONF_NAME], CONF_HOST: data[CONF_HOST]}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Logitech Harmony Hub."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        """Initialize the Harmony config flow."""
        self.harmony_config = {}

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_HOST])
            # Abort if already setup
            self._abort_if_unique_id_configured(
                updates={CONF_HOST: user_input[CONF_HOST]}
            )

            # If we are importing we need to keep their options
            options = {}
            if ATTR_ACTIVITY in user_input:
                options[ATTR_ACTIVITY] = user_input[ATTR_ACTIVITY]
            if ATTR_DELAY_SECS in user_input:
                options[ATTR_DELAY_SECS] = user_input[ATTR_DELAY_SECS]

            _LOGGER.debug(
                "ABOUT TO USER: user_input:%s options:%s", user_input, options,
            )

            try:
                info = await validate_input(self.hass, user_input)
                _LOGGER.debug(
                    "AFTER VALIDATE: user_input:%s options:%s info: %s",
                    user_input,
                    options,
                    info,
                )
                config_entry = self.async_create_entry(title=info[CONF_NAME], data=info)
                if options:
                    self.hass.config_entries.async_update_entry(
                        config_entry, data=info, options=options
                    )
                return config_entry
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

            _LOGGER.debug("FLOW FAILED: %s", user_input)

        # Return form
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_ssdp(self, discovery_info):
        """Handle a discovered Harmony device."""
        parsed_url = urlparse(discovery_info[ssdp.ATTR_SSDP_LOCATION])
        friendly_name = discovery_info[ssdp.ATTR_UPNP_FRIENDLY_NAME]
        await self.async_set_unique_id(parsed_url.hostname)
        # Abort if already setup
        self._abort_if_unique_id_configured(updates={CONF_HOST: parsed_url.hostname})
        # pylint: disable=no-member
        self.context["title_placeholders"] = {"name": friendly_name}

        self.harmony_config = {
            CONF_HOST: parsed_url.hostname,
            CONF_NAME: friendly_name,
        }

        return await self.async_step_link()

    async def async_step_link(self, user_input=None):
        """Attempt to link with the Harmony."""
        errors = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, self.harmony_config)
                return self.async_create_entry(title=info[CONF_NAME], data=info)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="link",
            errors=errors,
            description_placeholders={
                "name": self.harmony_config[CONF_NAME],
                "host": self.harmony_config[CONF_HOST],
            },
        )

    async def async_step_import(self, user_input):
        """Handle import from yaml."""
        _LOGGER.debug("ABOUT TO IMPORT: user_input:%s", user_input)
        await self.async_set_unique_id(user_input[CONF_HOST])
        self._abort_if_unique_id_configured()
        _LOGGER.debug("MADE IT THOUGH ABORT: user_input:%s", user_input)
        return await self.async_step_user(user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a option flow for Harmony."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # TODO: see how heos looks at hass.data to find the ips
        # we can prevent a list of activities for the default activity
        data_schema = vol.Schema(
            {
                vol.Optional(
                    ATTR_DELAY_SECS,
                    default=self.config_entry.options.get(
                        ATTR_DELAY_SECS, DEFAULT_DELAY_SECS
                    ),
                ): vol.Coerce(float),
                vol.Optional(
                    ATTR_ACTIVITY, default=self.config_entry.options.get(ATTR_ACTIVITY),
                ): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=data_schema)


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""
