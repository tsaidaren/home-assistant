"""The tests for the august platform."""

from august.exceptions import AugustApiHTTPError

from homeassistant.components.lock import DOMAIN as LOCK_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_LOCK,
    SERVICE_UNLOCK,
    STATE_LOCKED,
    STATE_ON,
)
from homeassistant.exceptions import HomeAssistantError

from tests.components.august.mocks import (
    _create_august_with_devices,
    _mock_doorsense_enabled_august_lock_detail,
    _mock_doorsense_missing_august_lock_detail,
    _mock_inoperative_august_lock_detail,
    _mock_operative_august_lock_detail,
)


async def test_unlock_throws_august_api_http_error(hass):
    """Test unlock throws correct error on http error."""
    mocked_lock_detail = await _mock_operative_august_lock_detail(hass)

    def _unlock_return_activities_side_effect(access_token, device_id):
        raise AugustApiHTTPError("This should bubble up as its user consumable")

    await _create_august_with_devices(
        hass,
        [mocked_lock_detail],
        api_call_side_effects={
            "unlock_return_activities": _unlock_return_activities_side_effect
        },
    )
    last_err = None
    data = {ATTR_ENTITY_ID: "lock.a6697750d607098bae8d6baa11ef8063_name"}
    try:
        await hass.services.async_call(LOCK_DOMAIN, SERVICE_UNLOCK, data, blocking=True)
    except HomeAssistantError as err:
        last_err = err
    assert (
        str(last_err)
        == "A6697750D607098BAE8D6BAA11EF8063 Name: This should bubble up as its user consumable"
    )


async def test_lock_throws_august_api_http_error(hass):
    """Test lock throws correct error on http error."""
    mocked_lock_detail = await _mock_operative_august_lock_detail(hass)

    def _lock_return_activities_side_effect(access_token, device_id):
        raise AugustApiHTTPError("This should bubble up as its user consumable")

    await _create_august_with_devices(
        hass,
        [mocked_lock_detail],
        api_call_side_effects={
            "lock_return_activities": _lock_return_activities_side_effect
        },
    )
    last_err = None
    data = {ATTR_ENTITY_ID: "lock.a6697750d607098bae8d6baa11ef8063_name"}
    try:
        await hass.services.async_call(LOCK_DOMAIN, SERVICE_LOCK, data, blocking=True)
    except HomeAssistantError as err:
        last_err = err
    assert (
        str(last_err)
        == "A6697750D607098BAE8D6BAA11EF8063 Name: This should bubble up as its user consumable"
    )


async def test_inoperative_locks_are_filtered_out(hass):
    """Ensure inoperative locks do not get setup."""
    august_operative_lock = await _mock_operative_august_lock_detail(hass)
    august_inoperative_lock = await _mock_inoperative_august_lock_detail(hass)
    await _create_august_with_devices(
        hass, [august_operative_lock, august_inoperative_lock]
    )

    lock_abc_name = hass.states.get("lock.abc_name")
    assert lock_abc_name is None
    lock_a6697750d607098bae8d6baa11ef8063_name = hass.states.get(
        "lock.a6697750d607098bae8d6baa11ef8063_name"
    )
    assert lock_a6697750d607098bae8d6baa11ef8063_name.state == STATE_LOCKED


# import pprint
# import json
# from homeassistant.helpers.json import JSONEncoder
# pprint.pprint(json.dumps(hass.states.async_all(), cls=JSONEncoder))


async def test_lock_has_doorsense(hass):
    """Check to see if a lock has doorsense."""
    doorsenselock = await _mock_doorsense_enabled_august_lock_detail(hass)
    nodoorsenselock = await _mock_doorsense_missing_august_lock_detail(hass)
    await _create_august_with_devices(hass, [doorsenselock, nodoorsenselock])
    import pprint
    import json
    from homeassistant.helpers.json import JSONEncoder

    pprint.pprint(json.dumps(hass.states.async_all(), cls=JSONEncoder))

    binary_sensor_online_with_doorsense_name_open = hass.states.get(
        "binary_sensor.online_with_doorsense_name_open"
    )
    assert binary_sensor_online_with_doorsense_name_open.state == STATE_ON
    binary_sensor_missing_doorsense_id_name_open = hass.states.get(
        "binary_sensor.missing_doorsense_id_name_open"
    )
    assert binary_sensor_missing_doorsense_id_name_open is None
