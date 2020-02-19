"""The lock tests for the august platform."""

import json
from unittest import mock
from unittest.mock import MagicMock

from august.lock import LockDetail

from homeassistant.components.august import (
    CONF_LOGIN_METHOD,
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
)
from homeassistant.helpers.json import JSONEncoder
from homeassistant.setup import async_setup_component

from tests.components.august.mocks import (
    _mock_august_authentication,
    _mock_august_lock,
    _mock_lock_from_fixture,
)


def get_config():
    """Return a default august config."""
    return {
        DOMAIN: {
            CONF_LOGIN_METHOD: "email",
            CONF_USERNAME: "mocked_username",
            CONF_PASSWORD: "mocked_password",
        }
    }


async def test_one_lock(hass):
    """Test creation of a lock with doorsense and bridge."""
    lock_one = await _mock_lock_from_fixture(
        hass, "get_lock.online_with_doorsense.json"
    )
    lock_details = [lock_one]
    await _create_august_with_lock_details(hass, lock_details)
    import pprint

    pprint.pprint(json.dumps(hass.states.async_all(), cls=JSONEncoder))
    lock_abc_name = hass.states.get("lock.abc_name")
    pprint.pprint(lock_abc_name.attributes)
    # assert lock_abc_name.attributes.battery_level == 92
    # assert lock_abc_name.attributes.available == True
    # assert lock_abc_name.attributes.locked == True

    # binary_sensor_abc_name = hass.states.get("binary_sensor.abc_name_open")
    # pprint.pprint(lock_abc_name)
    # pprint.pprint(binary_sensor_abc_name)
    # raise


@mock.patch("homeassistant.components.august.Api")
@mock.patch("homeassistant.components.august.Authenticator.authenticate")
async def _mock_setup_august(hass, api_mocks_callback, authenticate_mock, api_mock):
    """Set up august integration."""
    authenticate_mock.side_effect = MagicMock(
        return_value=_mock_august_authentication("original_token", 1234)
    )
    api_mocks_callback(api_mock)
    assert await async_setup_component(hass, DOMAIN, get_config())
    await hass.async_block_till_done()
    return True


async def _create_august_with_lock_details(hass, lock_details):
    locks = []
    for lock in lock_details:
        if isinstance(lock, LockDetail):
            locks.append(_mock_august_lock(lock.device_id))

    def api_mocks_callback(api):
        def get_lock_detail_side_effect(access_token, device_id):
            for lock in lock_details:
                if isinstance(lock, LockDetail) and lock.device_id == device_id:
                    return lock

        api_instance = MagicMock()
        api_instance.get_lock_detail.side_effect = get_lock_detail_side_effect
        api_instance.get_operable_locks.return_value = locks
        api_instance.get_doorbells.return_value = []
        api.return_value = api_instance

    await _mock_setup_august(hass, api_mocks_callback)

    return True
