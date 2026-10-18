import logging
from unittest.mock import Mock, call, patch

import pytest

from app.keycloak import KeycloakUnavailable
from app.main import cleanup_deleted_users


@pytest.mark.parametrize("failed_user_id", ["first", "second"])
def test_cleanup_continues_after_user_deletion_failure(failed_user_id, caplog):
    kc = Mock()
    kc.get_users_scheduled_for_deletion.return_value = [
        {"id": user_id, "username": user_id}
        for user_id in ("first", "second", "third")
    ]

    def delete_user(user_id):
        if user_id == failed_user_id:
            raise KeycloakUnavailable("keycloak responded with 503")
        return True

    kc.hard_delete_user.side_effect = delete_user

    with (
        patch("app.config.get_settings"),
        patch("app.keycloak.KeycloakClient", return_value=kc),
        caplog.at_level(logging.INFO),
    ):
        cleanup_deleted_users()

    assert kc.hard_delete_user.call_args_list == [
        call("first"), call("second"), call("third")
    ]
    kc.close.assert_called_once_with()
    assert any(
        record.levelno == logging.ERROR and failed_user_id in record.getMessage()
        for record in caplog.records
    )
    assert "Hard-deleted user third" in caplog.text
