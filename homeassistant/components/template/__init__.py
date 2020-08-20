"""The template component."""

import asyncio
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

        add_tasks = []

        for platform_setup in hass.data[PLATFORM_STORAGE_KEY].values():
            platform, create_entities = platform_setup

            await platform.async_reset()

            integration = await async_get_integration(hass, platform.domain)

            conf = await conf_util.async_process_component_config(
                hass, unprocessed_conf, integration
            )
            if not conf:
                continue

            # Extract only the config for the template, ignore the rest.
            for p_type, p_config in config_per_platform(conf, platform.domain):
                if p_type != DOMAIN:
                    continue

                entities = await create_entities(hass, p_config)

                add_tasks.append(
                    hass.async_create_task(platform.async_add_entities(entities))
                )

        await asyncio.gather(*add_tasks)

        hass.bus.async_fire(EVENT_TEMPLATE_RELOADED, context=call.context)

    hass.helpers.service.async_register_admin_service(
        DOMAIN, SERVICE_RELOAD, _reload_config
    )


async def async_setup_platform_reloadable(
    hass, config, async_add_entities, platform, create_entities
):
    """Template platform with reloadability."""

    _LOGGER.error(
        "async_setup_platform_reloadable: platform.domain=%s platform.platform=%s platform.platform_name=%s",
        platform.domain,
        platform.platform,
        platform.platform_name,
    )

    hass.data.setdefault(PLATFORM_STORAGE_KEY, {})

    await _async_setup_reload_service(hass)

    # This platform can be loaded multiple times. Only first time register the service.
    if platform.domain not in hass.data[PLATFORM_STORAGE_KEY]:
        hass.data[PLATFORM_STORAGE_KEY][platform.domain] = (
            platform,
            create_entities,
        )

    async_add_entities(await create_entities(hass, config))
