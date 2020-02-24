"""Handle August connection setup and authentication."""

import asyncio
from exceptions import CannotConnect, InvalidAuth, RequireValidation
import logging

from august.api import Api
from august.authenticator import AuthenticationState, Authenticator
from const import (
    CONF_ACCESS_TOKEN_CACHE_FILE,
    CONF_INSTALL_ID,
    CONF_LOGIN_METHOD,
    CONF_PASSWORD,
    CONF_TIMEOUT,
    CONF_USERNAME,
    DEFAULT_AUGUST_CONFIG_FILE,
    VALIDATION_CODE_KEY,
)
from requests import RequestException, Session

_LOGGER = logging.getLogger(__name__)


class AugustGateway:
    """Handle the connection to August."""

    def __init__(self, hass):
        """Init the connection."""
        try:
            self._api_http_session = Session()
        except RequestException as ex:
            _LOGGER.warning("Creating HTTP session failed with: %s", str(ex))
        self._token_refresh_lock = asyncio.Lock()
        self._hass = hass

    @property
    def authenticator(self):
        """August authentication object from py-august."""
        return self._authenticator

    @property
    def authentication(self):
        """August authentication object from py-august."""
        return self._authentication

    @property
    def access_token(self):
        """Access token for the api."""
        return self._authentication.access_token

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

    def setup(self, conf):
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
                    "." + self._username + DEFAULT_AUGUST_CONFIG_FILE
                )

            self._api = Api(timeout=self._timeout, http_session=self._api_http_session)

            self._authenticator = Authenticator(
                self._api,
                self._login_method,
                self._username,
                self._password,
                install_id=self._install_id,
                access_token_cache_file=self._hass.config.path(
                    self._access_token_cache_file
                ),
            )

    async def async_authenticate(self):
        """Authenticate with the details provided to setup."""
        self._authentication = None
        try:
            self._authentication = await self._hass.async_add_executor_job(
                self.authenticator.authenticate
            )
        except RequestException as ex:
            _LOGGER.error("Unable to connect to August service: %s", str(ex))
            raise CannotConnect

        if self._authentication.state == AuthenticationState.BAD_PASSWORD:
            raise InvalidAuth

        if self._authentication.state == AuthenticationState.REQUIRES_VALIDATION:
            raise RequireValidation

        if self._authentication.state != AuthenticationState.AUTHENTICATED:
            _LOGGER.error(
                "Unknown authentication state: " + str(self._authentication.state)
            )
            raise InvalidAuth

        return self._authentication

    async def async_refresh_access_token_if_needed(self):
        """Refresh the august access token if needed."""
        if self.authenticator.should_refresh():
            async with self._token_refresh_lock:
                await self._hass.async_add_executor_job(self._refresh_access_token)

    def _refresh_access_token(self):
        refreshed_authentication = self.authenticator.refresh_access_token(force=False)
        _LOGGER.info(
            "Refreshed august access token. The old token expired at %s, and the new token expires at %s",
            self.authentication.access_token_expires,
            refreshed_authentication.access_token_expires,
        )
        self.authentication = refreshed_authentication

    def _close_http_session(self):
        """Close API sessions used to connect to August."""
        if self._api_http_session:
            try:
                self._api_http_session.close()
            except RequestException:
                pass

    def __del__(self):
        """Close out the http session on destroy."""
        self._close_http_session()
        return
