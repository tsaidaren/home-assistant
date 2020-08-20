"""The template component."""

import logging

from homeassistant import config as conf_util
from homeassistant.const import SERVICE_RELOAD
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_per_platform
from homeassistant.loader import async_get_integration

from .const import DOMAIN, EVENT_TEMPLATE_RELOADED, PLATFORM_STORAGE_KEY

_LOGGER = logging.getLogger(__name__)


async def _async_setup_reload_service(hass):
    if hass.services.has_service(DOMAIN, SERVICE_RELOAD):
        return

    async def _reload_config(call):
        """Reload the template platform config."""
        try:
            unprocessed_conf = await conf_util.async_hass_config_yaml(hass)
        except HomeAssistantError as err:
            _LOGGER.error(err)
            return

        for platform_setup in hass.data[PLATFORM_STORAGE_KEY].values():
            async_add_entities, platform, process_config = platform_setup

            integration = await async_get_integration(hass, platform.domain)

            conf = await conf_util.async_process_component_config(
                hass, unprocessed_conf, integration
            )
            if not conf:
                continue

            await platform.async_reset()

            # Extract only the config for the template, ignore the rest.
            for p_type, p_config in config_per_platform(conf, platform.domain):
                if p_type != DOMAIN:
                    continue
                _LOGGER.error(
                    ["_reload_platform", "want", "p_type", p_type, "p_config", p_config]
                )

                await process_config(hass, p_config, async_add_entities)

        hass.bus.async_fire(EVENT_TEMPLATE_RELOADED, context=call.context)

    hass.helpers.service.async_register_admin_service(
        DOMAIN, SERVICE_RELOAD, _reload_config
    )


async def async_setup_platform_reloadable(
    hass, config, async_add_entities, platform, process_config
):
    """Template platform with reloadability."""
    hass.data.setdefault(PLATFORM_STORAGE_KEY, {})

    await _async_setup_reload_service(hass)

    # This platform can be loaded multiple times. Only first time register the service.
    if platform.domain not in hass.data[PLATFORM_STORAGE_KEY]:
        hass.data[PLATFORM_STORAGE_KEY][platform.domain] = (
            async_add_entities,
            platform,
            process_config,
        )

    return await process_config(hass, config, async_add_entities)
