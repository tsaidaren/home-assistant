"""The rest component."""

import asyncio
import logging

from homeassistant.const import SERVICE_RELOAD
from homeassistant.helpers.reload import async_reload_integration_platforms

DOMAIN = "rest"
PLATFORMS = ["binary_sensor", "notify", "sensor", "switch"]
EVENT_REST_RELOADED = "event_rest_reloaded"

_LOGGER = logging.getLogger(__name__)


async def async_setup_reload_service(hass):
    """Create the reload service for the reset domain."""

    if hass.services.has_service(DOMAIN, SERVICE_RELOAD):
        return

    async def _reload_config(call):
        """Reload the rest platform config."""

        await async_reload_integration_platforms(hass, DOMAIN, PLATFORMS)
        hass.bus.async_fire(EVENT_REST_RELOADED, context=call.context)

    hass.helpers.service.async_register_admin_service(
        DOMAIN, SERVICE_RELOAD, _reload_config
    )


def setup_reload_service(hass):
    """Sync version of async_setup_reload_service."""

    asyncio.run_coroutine_threadsafe(
        async_setup_reload_service(hass), hass.loop,
    ).result()
