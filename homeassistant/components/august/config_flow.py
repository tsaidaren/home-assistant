"""Config flow for August integration."""
import logging

from august.api import Api
from august.authenticator import AuthenticationState, Authenticator, ValidationResult
from requests import RequestException, Session
import voluptuous as vol

from homeassistant import config_entries, core, exceptions

from . import (
    AUGUST_CONFIG_FILE,
    CONF_ACCESS_TOKEN_CACHE_FILE,
    CONF_INSTALL_ID,
    CONF_LOGIN_METHOD,
    CONF_PASSWORD,
    CONF_TIMEOUT,
    CONF_USERNAME,
    DEFAULT_TIMEOUT,
    VALIDATION_CODE_KEY,
)
from . import DOMAIN  # pylint:disable=unused-import

_LOGGER = logging.getLogger(__name__)

LOGIN_METHODS = ["phone", "email"]
DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_LOGIN_METHOD, default="phone"): vol.In(LOGIN_METHODS),
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.Coerce(int),
    }
)


async def validate_input(
    hass: core.HomeAssistant, data, august_connection,
):
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    """Request configuration steps from the user."""

    code = data.get(VALIDATION_CODE_KEY)

    if code is not None:
        result = await hass.async_add_executor_job(
            august_connection.authenticator.validate_verification_code, code
        )
        _LOGGER.debug("Verification code validation: %s", result)
        if result != ValidationResult.VALIDATED:
            raise RequireValidation

    authentication = None
    try:
        authentication = await hass.async_add_executor_job(
            august_connection.authenticator.authenticate
        )
    except RequestException as ex:
        _LOGGER.error("Unable to connect to August service: %s", str(ex))
        raise CannotConnect

    if authentication.state == AuthenticationState.BAD_PASSWORD:
        raise InvalidAuth

    if authentication.state == AuthenticationState.REQUIRES_VALIDATION:
        _LOGGER.debug(
            "Requesting new verification code for %s via %s",
            data.get(CONF_USERNAME),
            data.get(CONF_LOGIN_METHOD),
        )
        await hass.async_add_executor_job(
            august_connection.authenticator.send_verification_code
        )
        raise RequireValidation

    return {
        "title": data.get(CONF_USERNAME),
        "data": august_connection.config_entry(),
    }


class AugustConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for August."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Store an AugustConnection()."""
        self._august_connection = AugustConnection()
        super().__init__()

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            self._august_connection.setup(user_input)

            try:
                info = await validate_input(
                    self.hass, user_input, self._august_connection,
                )
                await self.async_set_unique_id(user_input[CONF_USERNAME])
                return self.async_create_entry(title=info["title"], data=info["data"])
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except RequireValidation:
                self.user_auth_details = user_input

                return await self.async_step_validation()
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_validation(self, user_input=None):
        """Handle validation (2fa) step."""
        if user_input:
            return await self.async_step_user({**self.user_auth_details, **user_input})

        return self.async_show_form(
            step_id="validation",
            data_schema=vol.Schema(
                {vol.Required(VALIDATION_CODE_KEY): vol.All(str, vol.Strip)}
            ),
            description_placeholders={
                CONF_USERNAME: self.user_auth_details.get(CONF_USERNAME),
                CONF_LOGIN_METHOD: self.user_auth_details.get(CONF_LOGIN_METHOD),
            },
        )

    async def async_step_import(self, user_input):
        """Handle import."""
        await self.async_set_unique_id(user_input[CONF_USERNAME])
        self._abort_if_unique_id_configured()

        return await self.async_step_user(user_input)


class AugustConnection:
    """Handle the connection to August."""

    def __init__(self):
        """Init the connection."""
        self._api_http_session = Session()

    @property
    def authenticator(self):
        """August authentication object from py-august."""
        return self._authenticator

    @property
    def api(self):
        """August api object from py-august."""
        return self._api

    @property
    def access_token_cache_file(self):
        """Basename of the access token cache file."""
        return self._access_token_cache_file

    def config_entry(self):
        """Config entry."""
        return {
            CONF_LOGIN_METHOD: self._login_method,
            CONF_USERNAME: self._username,
            CONF_PASSWORD: self._password,
            CONF_INSTALL_ID: self._install_id,
            CONF_TIMEOUT: self._timeout,
            CONF_ACCESS_TOKEN_CACHE_FILE: self._access_token_cache_file,
        }

    def setup(self, hass, conf):
        """Create the api and authenticator objects."""
        if not conf.get(VALIDATION_CODE_KEY):
            self._login_method = conf.get(CONF_LOGIN_METHOD)
            self._username = conf.get(CONF_USERNAME)
            self._password = conf.get(CONF_PASSWORD)
            self._install_id = conf.get(CONF_INSTALL_ID)
            self._timeout = conf.get(CONF_TIMEOUT)

            self._access_token_cache_file = conf.get(CONF_ACCESS_TOKEN_CACHE_FILE)
            if self._access_token_cache_file is None:
                self._access_token_cache_file = (
                    "." + self._username + AUGUST_CONFIG_FILE
                )

            self._api = Api(timeout=self._timeout, http_session=self._api_http_session,)

            self._authenticator = Authenticator(
                self._api,
                self._login_method,
                self._username,
                self._password,
                install_id=self._install_id,
                access_token_cache_file=self.hass.config.path(
                    self._access_token_cache_file
                ),
            )

    def close_http_session(self):
        """Close API sessions used to connect to August."""
        _LOGGER.debug("Closing August HTTP sessions")
        if self._api_http_session:
            try:
                self._api_http_session.close()
            except RequestException:
                pass

    def __del__(self):
        """Close out the http session on destroy."""
        self.close_http_session()
        return


class RequireValidation(exceptions.HomeAssistantError):
    """Error to indicate we require validation (2fa)."""


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
