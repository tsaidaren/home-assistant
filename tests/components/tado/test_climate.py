"""The climate tests for the tado platform."""


from tests.components.tado.mocks import _mock_tado_climate_zone_from_fixture


async def test_smartac3_smart_mode(hass):
    """Test smart ac smart mode."""
    smartac3_smart_mode = await _mock_tado_climate_zone_from_fixture(
        hass, "smartac3.smart_mode.json"
    )
    assert smartac3_smart_mode.preparation is False
    assert smartac3_smart_mode.open_window is False
    assert smartac3_smart_mode.open_window_attr == {}
    assert smartac3_smart_mode.current_temp == 24.43
    assert smartac3_smart_mode.current_temp_timestamp == "2020-03-05T03:50:24.769Z"
    assert smartac3_smart_mode.connection is None
    assert smartac3_smart_mode.tado_mode == "HOME"
    assert smartac3_smart_mode.overlay_active is False
    assert smartac3_smart_mode.overlay_termination_type is None
    assert smartac3_smart_mode.current_humidity == 60.0
    assert smartac3_smart_mode.current_humidity_timestamp == "2020-03-05T03:50:24.769Z"
    assert smartac3_smart_mode.ac_power_timestamp == "2020-03-05T03:52:22.253Z"
    assert smartac3_smart_mode.heating_power_timestamp is None
    assert smartac3_smart_mode.ac_power == "OFF"
    assert smartac3_smart_mode.heating_power is None
    assert smartac3_smart_mode.heating_power_percentage is None
    assert smartac3_smart_mode.is_away is False
    assert smartac3_smart_mode.power == "ON"
    assert smartac3_smart_mode.current_hvac_action == "off"
    assert smartac3_smart_mode.current_tado_fan_speed == "MIDDLE"
    assert smartac3_smart_mode.link == "ONLINE"
    assert smartac3_smart_mode.current_tado_hvac_mode == "SMART_SCHEDULE"
    assert smartac3_smart_mode.target_temp == 20.0
    assert smartac3_smart_mode.available is True


async def test_smartac3_cool_mode(hass):
    """Test smart ac cool mode."""
    smartac3_cool_mode = await _mock_tado_climate_zone_from_fixture(
        hass, "smartac3.cool_mode.json"
    )
    assert smartac3_cool_mode.preparation is False
    assert smartac3_cool_mode.open_window is False
    assert smartac3_cool_mode.open_window_attr == {}
    assert smartac3_cool_mode.current_temp == 24.76
    assert smartac3_cool_mode.current_temp_timestamp == "2020-03-05T03:57:38.850Z"
    assert smartac3_cool_mode.connection is None
    assert smartac3_cool_mode.tado_mode == "HOME"
    assert smartac3_cool_mode.overlay_active is True
    assert smartac3_cool_mode.overlay_termination_type == "TADO_MODE"
    assert smartac3_cool_mode.current_humidity == 60.9
    assert smartac3_cool_mode.current_humidity_timestamp == "2020-03-05T03:57:38.850Z"
    assert smartac3_cool_mode.ac_power_timestamp == "2020-03-05T04:01:07.162Z"
    assert smartac3_cool_mode.heating_power_timestamp is None
    assert smartac3_cool_mode.ac_power == "ON"
    assert smartac3_cool_mode.heating_power is None
    assert smartac3_cool_mode.heating_power_percentage is None
    assert smartac3_cool_mode.is_away is False
    assert smartac3_cool_mode.power == "ON"
    assert smartac3_cool_mode.current_hvac_action == "cooling"
    assert smartac3_cool_mode.current_tado_fan_speed == "AUTO"
    assert smartac3_cool_mode.link == "ONLINE"
    assert smartac3_cool_mode.current_tado_hvac_mode == "COOL"
    assert smartac3_cool_mode.target_temp == 17.78
    assert smartac3_cool_mode.available is True


async def test_smartac3_auto_mode(hass):
    """Test smart ac cool mode."""
    smartac3_auto_mode = await _mock_tado_climate_zone_from_fixture(
        hass, "smartac3.auto_mode.json"
    )
    assert smartac3_auto_mode.preparation is False
    assert smartac3_auto_mode.open_window is False
    assert smartac3_auto_mode.open_window_attr == {}
    assert smartac3_auto_mode.current_temp == 24.8
    assert smartac3_auto_mode.current_temp_timestamp == "2020-03-05T03:55:38.160Z"
    assert smartac3_auto_mode.connection is None
    assert smartac3_auto_mode.tado_mode == "HOME"
    assert smartac3_auto_mode.overlay_active is True
    assert smartac3_auto_mode.overlay_termination_type == "TADO_MODE"
    assert smartac3_auto_mode.current_humidity == 62.5
    assert smartac3_auto_mode.current_humidity_timestamp == "2020-03-05T03:55:38.160Z"
    assert smartac3_auto_mode.ac_power_timestamp == "2020-03-05T03:56:38.627Z"
    assert smartac3_auto_mode.heating_power_timestamp is None
    assert smartac3_auto_mode.ac_power == "ON"
    assert smartac3_auto_mode.heating_power is None
    assert smartac3_auto_mode.heating_power_percentage is None
    assert smartac3_auto_mode.is_away is False
    assert smartac3_auto_mode.power == "ON"
    assert smartac3_auto_mode.current_hvac_action == "cooling"
    assert smartac3_auto_mode.current_tado_fan_speed == "AUTO"
    assert smartac3_auto_mode.link == "ONLINE"
    assert smartac3_auto_mode.current_tado_hvac_mode == "AUTO"
    assert smartac3_auto_mode.target_temp is None
    assert smartac3_auto_mode.available is True


async def test_ac_issue_32294_heat_mode(hass):
    """Test smart ac cool mode."""
    ac_issue_32294_heat_mode = await _mock_tado_climate_zone_from_fixture(
        hass, "ac_issue_32294.heat_mode.json"
    )
    assert ac_issue_32294_heat_mode.preparation is False
    assert ac_issue_32294_heat_mode.open_window is False
    assert ac_issue_32294_heat_mode.open_window_attr == {}
    assert ac_issue_32294_heat_mode.current_temp == 21.82
    assert ac_issue_32294_heat_mode.current_temp_timestamp == "2020-02-29T22:51:05.016Z"
    assert ac_issue_32294_heat_mode.connection is None
    assert ac_issue_32294_heat_mode.tado_mode == "HOME"
    assert ac_issue_32294_heat_mode.overlay_active is False
    assert ac_issue_32294_heat_mode.overlay_termination_type is None
    assert ac_issue_32294_heat_mode.current_humidity == 40.4
    assert (
        ac_issue_32294_heat_mode.current_humidity_timestamp
        == "2020-02-29T22:51:05.016Z"
    )
    assert ac_issue_32294_heat_mode.ac_power_timestamp == "2020-02-29T22:50:34.850Z"
    assert ac_issue_32294_heat_mode.heating_power_timestamp is None
    assert ac_issue_32294_heat_mode.ac_power == "ON"
    assert ac_issue_32294_heat_mode.heating_power is None
    assert ac_issue_32294_heat_mode.heating_power_percentage is None
    assert ac_issue_32294_heat_mode.is_away is False
    assert ac_issue_32294_heat_mode.power == "ON"
    assert ac_issue_32294_heat_mode.current_hvac_action == "heating"
    assert ac_issue_32294_heat_mode.current_tado_fan_speed == "AUTO"
    assert ac_issue_32294_heat_mode.link == "ONLINE"
    assert ac_issue_32294_heat_mode.current_tado_hvac_mode == "SMART_SCHEDULE"
    assert ac_issue_32294_heat_mode.target_temp == 25.0
    assert ac_issue_32294_heat_mode.available is True
