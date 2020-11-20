"""The waze_travel_time component."""
import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Config, HomeAssistant

PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, config: Config) -> bool:
    """Component setup."""
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Load the saved entities."""
    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, platform)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(config_entry, platform)
                for platform in PLATFORMS
            ]
        )
    )

    return unload_ok
