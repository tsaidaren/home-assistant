"""The sensor tests for the august platform."""

from tests.components.august.mocks import (
    _create_august_with_devices,
    _mock_doorbell_from_fixture,
)


async def test_create_doorbell(hass):
    """Test creation of a doorbell."""
    doorbell_one = await _mock_doorbell_from_fixture(hass, "get_doorbell.json")
    doorbell_details = [doorbell_one]
    await _create_august_with_devices(hass, doorbell_details=doorbell_details)

    import pprint
    from homeassistant.helpers.json import JSONEncoder
    import json

    pprint.pprint(json.dumps(hass.states.async_all(), cls=JSONEncoder))
    sensor_k98gidt45gul_name_battery = hass.states.get(
        "sensor.k98gidt45gul_name_battery"
    )
    assert sensor_k98gidt45gul_name_battery.state == "96"
    assert sensor_k98gidt45gul_name_battery.attributes["unit_of_measurement"] == "%"


async def test_create_doorbell_offline(hass):
    """Test creation of a doorbell that is offline."""
    doorbell_one = await _mock_doorbell_from_fixture(hass, "get_doorbell.offline.json")
    doorbell_details = [doorbell_one]
    await _create_august_with_devices(hass, doorbell_details=doorbell_details)

    import pprint
    from homeassistant.helpers.json import JSONEncoder
    import json

    pprint.pprint(json.dumps(hass.states.async_all(), cls=JSONEncoder))
    sensor_tmt100_name_battery = hass.states.get("sensor.tmt100_name_battery")
    assert sensor_tmt100_name_battery.state == "81"
    assert sensor_tmt100_name_battery.attributes["unit_of_measurement"] == "%"
