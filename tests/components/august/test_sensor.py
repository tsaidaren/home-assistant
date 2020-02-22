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
    assert sensor_k98gidt45gul_name_battery.state == 88
    assert sensor_k98gidt45gul_name_battery.attributes.unit_of_measure == "%"
