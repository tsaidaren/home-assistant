"""The tests for the august platform."""
from unittest.mock import MagicMock

from homeassistant.components import august

from tests.components.august.mocks import (
    MockAugustData,
    _mock_august_authentication,
    _mock_august_authenticator,
)


def test_get_lock_name():
    """Get the lock name from August data."""
    data = MockAugustData(last_lock_status_update_timestamp=1)
    assert data.get_lock_name("mockdeviceid1") == "Mocked Lock 1"


def test__refresh_access_token():
    """Test refresh of the access token."""
    authentication = _mock_august_authentication("original_token", 1234)
    authenticator = _mock_august_authenticator()
    data = august.AugustData(
        MagicMock(name="hass"), MagicMock(name="api"), authentication, authenticator
    )
    data._refresh_access_token_if_needed()
    authenticator.refresh_access_token.assert_not_called()

    authenticator.should_refresh.return_value = 1
    authenticator.refresh_access_token.return_value = _mock_august_authentication(
        "new_token", 5678
    )
    data._refresh_access_token_if_needed()
    authenticator.refresh_access_token.assert_called()
    assert data._access_token == "new_token"
    assert data._access_token_expires == 5678
