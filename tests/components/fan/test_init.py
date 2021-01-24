"""Tests for fan platforms."""

import pytest

from homeassistant.components.fan import FanEntity


class BaseFan(FanEntity):
    """Implementation of the abstract FanEntity."""

    def __init__(self):
        """Initialize the fan."""


def test_fanentity():
    """Test fan entity methods."""
    fan = BaseFan()
    assert fan.state == "off"
    assert len(fan.speed_list) == 0
    assert len(fan.preset_modes) == 0
    assert fan.supported_features == 0
    assert fan.capability_attributes == {}
    # Test set_speed not required
    with pytest.raises(NotImplementedError):
        fan.oscillate(True)
    with pytest.raises(NotImplementedError):
        fan.set_speed("slow")
    with pytest.raises(NotImplementedError):
        fan.set_percentage(0)
    with pytest.raises(NotImplementedError):
        fan.set_preset_mode("auto")
    with pytest.raises(NotImplementedError):
        fan.turn_on()
    with pytest.raises(NotImplementedError):
        fan.turn_off()


async def test_async_fanentity(hass):
    """Test async fan entity methods."""
    fan = BaseFan()
    fan.hass = hass
    assert fan.state == "off"
    assert len(fan.speed_list) == 0
    assert len(fan.preset_modes) == 0
    assert fan.supported_features == 0
    assert fan.capability_attributes == {}
    # Test set_speed not required
    with pytest.raises(NotImplementedError):
        await fan.async_oscillate(True)
    with pytest.raises(NotImplementedError):
        await fan.async_set_speed("slow")
    with pytest.raises(NotImplementedError):
        await fan.async_set_percentage(0)
    with pytest.raises(NotImplementedError):
        await fan.async_set_preset_mode("auto")
    with pytest.raises(NotImplementedError):
        await fan.async_turn_on()
    with pytest.raises(NotImplementedError):
        await fan.async_turn_off()
