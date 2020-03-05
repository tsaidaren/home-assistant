"""The lock tests for the august platform."""


from tests.components.august.mocks import _mock_tado_climate_zone_from_fixture


async def test_smartac3_smart_mode(hass):
    """Test smart ac smart mode."""
    smartac3_smart_mode = _mock_tado_climate_zone_from_fixture(
        "smartac3.smart_mode.json"
    )
    assert smartac3_smart_mode.mode == "3"


async def test_smartac3_cool_mode(hass):
    """Test smart ac cool mode."""
    smartac3_cool_mode = _mock_tado_climate_zone_from_fixture("smartac3.cool_mode.json")
    smartac3_cool_mode.mode == "3"
