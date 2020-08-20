"""The template component."""

import logging

from homeassistant import config as conf_util
from homeassistant.const import SERVICE_RELOAD
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_per_platform
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.loader import async_get_integration

from .const import DISPATCHER_RELOAD_TEMPLATE_PLATFORMS, DOMAIN, EVENT_TEMPLATE_RELOADED

_LOGGER = logging.getLogger(__name__)


async def _async_setup_reload_service(hass):
    if hass.services.has_service(DOMAIN, SERVICE_RELOAD):
        return

    async def _reload_config(call):
        async_dispatcher_send(hass, DISPATCHER_RELOAD_TEMPLATE_PLATFORMS)
        hass.bus.async_fire(EVENT_TEMPLATE_RELOADED, context=call.context)

    hass.helpers.service.async_register_admin_service(
        DOMAIN, SERVICE_RELOAD, _reload_config
    )


async def async_setup_platform_reloadable(
    hass, config, async_add_entities, platform, process_config
):
    """Template platform with reloadability."""
    # This platform can be loaded multiple times. Only first time register the service.
    await _async_setup_reload_service(hass)

    data_key = f"{DOMAIN}.{platform.domain}"

    if data_key not in hass.data:
        hass.data[data_key] = await _async_setup_for_reload(
            hass, async_add_entities, platform, process_config
        )

    return await process_config(hass, config, async_add_entities)


async def _async_setup_for_reload(hass, async_add_entities, platform, process_config):
    async def _reload_platform(*_):
        """Reload the template platform config."""
        try:
            conf = await conf_util.async_hass_config_yaml(hass)
        except HomeAssistantError as err:
            _LOGGER.error(err)
            return

        integration = await async_get_integration(hass, DOMAIN)

        conf = await conf_util.async_process_component_config(hass, conf, integration)

        if not conf:
            return

        await platform.async_reset()

        # Extract only the config for the template, ignore the rest.
        for p_type, p_config in config_per_platform(conf, platform.domain):
            if p_type != DOMAIN:
                continue
            _LOGGER.error(
                ["_reload_platform", "want", "p_type", p_type, "p_config", p_config]
            )

            await process_config(hass, p_config, async_add_entities)

    return async_dispatcher_connect(
        hass, DISPATCHER_RELOAD_TEMPLATE_PLATFORMS, _reload_platform
    )
