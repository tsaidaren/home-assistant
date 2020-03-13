"""Test the Rachio config flow."""
from asynctest import patch

from homeassistant import config_entries, setup
from homeassistant.components.rachio.config_flow import CannotConnect, InvalidAuth
from homeassistant.components.rachio.const import (
    CONF_CUSTOM_URL,
    CONF_MANUAL_RUN_MINS,
    DOMAIN,
)
from homeassistant.const import CONF_API_KEY


async def test_form(hass):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.rachio.config_flow.Rachio.person.getInfo",
        return_value=({"status": 200}, {"id": "myid"}),
    ), patch(
        "homeassistant.components.rachio.config_flow.Rachio.person.get",
        return_value=({"status": 200}, {"username": "myusername"}),
    ), patch(
        "homeassistant.components.rachio.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.rachio.async_setup_entry", return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_API_KEY: "api_key",
                CONF_CUSTOM_URL: "http://custom.url",
                CONF_MANUAL_RUN_MINS: 5,
            },
        )

    assert result2["type"] == "create_entry"
    assert result2["title"] == "Name of the device"
    assert result2["data"] == {
        CONF_API_KEY: "api_key",
        CONF_CUSTOM_URL: "http://custom.url",
        CONF_MANUAL_RUN_MINS: 5,
    }
    await hass.async_block_till_done()
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(hass):
    """Test we handle invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.rachio.config_flow.Rachio.person.getInfo",
        side_effect=InvalidAuth,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_API_KEY: "api_key",
                CONF_CUSTOM_URL: "http://custom.url",
                CONF_MANUAL_RUN_MINS: 5,
            },
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect(hass):
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.rachio.config_flow.Rachio.person.getInfo",
        side_effect=CannotConnect,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_API_KEY: "api_key",
                CONF_CUSTOM_URL: "http://custom.url",
                CONF_MANUAL_RUN_MINS: 5,
            },
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "cannot_connect"}
