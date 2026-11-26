"""Unit tests for PostgreSQL-backed authentication and admin user management."""

from datetime import datetime, timezone
from typing import Any
import pytest

from src.auth.service import AuthService, UserRecord, hash_password, verify_password


def test_should_hash_and_verify_password_with_argon2id() -> None:
    pw_hash = hash_password("dfpojk12#$")
    assert pw_hash.startswith("$argon2id$")
    assert verify_password("dfpojk12#$", pw_hash) is True
    assert verify_password("wrong_pass", pw_hash) is False
    assert verify_password("", pw_hash) is False
    assert verify_password("dfpojk12#$", "invalid_hash_format") is False


def test_should_verify_legacy_pbkdf2_hash_for_backward_compatibility() -> None:
    import hashlib

    salt = b"\x01" * 16
    dk = hashlib.pbkdf2_hmac("sha256", b"dfpojk12#$", salt, 260_000)
    legacy_hash = f"pbkdf2_sha256$260000${salt.hex()}${dk.hex()}"
    assert verify_password("dfpojk12#$", legacy_hash) is True
    assert verify_password("wrong", legacy_hash) is False


def test_should_reject_short_password_when_hashing() -> None:
    with pytest.raises(ValueError, match="co najmniej 6"):
        hash_password("12345")


def test_should_provision_users_table_and_default_inspe_admin(mock_db_cursor: Any) -> None:
    mock_db_cursor.fetchone.return_value = None

    AuthService.ensure_schema_and_admin()

    assert mock_db_cursor.execute.call_count == 3
    insert_sql, insert_params = mock_db_cursor.execute.call_args_list[2][0]
    assert "INSERT INTO users" in insert_sql
    assert insert_params[1] == "inspe"
    assert verify_password("dfpojk12#$", insert_params[2]) is True
    assert insert_params[3] == "admin"
    assert insert_params[4] is True


def test_should_authenticate_active_user_and_reject_invalid_or_inactive(mock_db_cursor: Any) -> None:
    valid_hash = hash_password("dfpojk12#$")
    now = datetime.now(timezone.utc)

    # 1. Valid admin login
    mock_db_cursor.fetchone.return_value = ("u-1", "inspe", valid_hash, "admin", True, now)
    user = AuthService.authenticate("inspe", "dfpojk12#$")
    assert user is not None
    assert user.username == "inspe"
    assert user.role == "admin"

    # 2. Wrong password
    assert AuthService.authenticate("inspe", "bad_password") is None

    # 3. Inactive account
    mock_db_cursor.fetchone.return_value = ("u-2", "jan", valid_hash, "user", False, now)
    assert AuthService.authenticate("jan", "dfpojk12#$") is None

    # 4. Unknown user / blank input
    mock_db_cursor.fetchone.return_value = None
    assert AuthService.authenticate("nieznany", "dfpojk12#$") is None
    assert AuthService.authenticate("   ", "dfpojk12#$") is None


def test_should_allow_admin_to_create_list_update_and_toggle_users(mock_db_cursor: Any) -> None:
    admin = UserRecord(id="a-1", username="inspe", role="admin")

    # create_user
    mock_db_cursor.fetchone.return_value = None
    created = AuthService.create_user(admin, "jan_kowalski", "Haslo123!", role="user")
    assert created.username == "jan_kowalski"
    assert created.role == "user"
    assert created.is_active is True

    # list_users
    now = datetime.now(timezone.utc)
    mock_db_cursor.fetchall.return_value = [
        ("a-1", "inspe", "admin", True, now),
        ("u-2", "jan_kowalski", "user", True, now),
    ]
    users = AuthService.list_users(admin)
    assert len(users) == 2
    assert users[1].username == "jan_kowalski"

    # update_user_password
    mock_db_cursor.fetchone.return_value = ("u-2",)
    AuthService.update_user_password(admin, "jan_kowalski", "NoweHaslo99!")

    # set_user_active
    mock_db_cursor.fetchone.return_value = ("u-2",)
    AuthService.set_user_active(admin, "jan_kowalski", False)

    # Admin cannot deactivate self
    with pytest.raises(ValueError, match="własnego konta"):
        AuthService.set_user_active(admin, "inspe", False)

    # delete_user (non-admin succeeds, self/admin blocked)
    mock_db_cursor.fetchone.return_value = ("u-2", "user")
    AuthService.delete_user(admin, "jan_kowalski")

    with pytest.raises(ValueError, match="własnego konta"):
        AuthService.delete_user(admin, "inspe")

    mock_db_cursor.fetchone.return_value = ("a-2", "admin")
    with pytest.raises(ValueError, match="administratora"):
        AuthService.delete_user(admin, "other_admin")


def test_should_block_non_admin_from_user_management_operations(mock_db_cursor: Any) -> None:
    regular_user = UserRecord(id="u-1", username="pracownik", role="user")

    with pytest.raises(PermissionError):
        AuthService.list_users(regular_user)

    with pytest.raises(PermissionError):
        AuthService.create_user(regular_user, "nowy", "Haslo123!")

    with pytest.raises(PermissionError):
        AuthService.update_user_password(regular_user, "inspe", "Haslo123!")

    with pytest.raises(PermissionError):
        AuthService.set_user_active(regular_user, "inspe", False)

    with pytest.raises(PermissionError):
        AuthService.delete_user(regular_user, "jan_kowalski")


def test_should_apply_user_table_changes_create_update_delete_and_protect_admin(
    mocker: Any,
) -> None:
    from src.ui.app import _apply_user_table_changes

    admin = UserRecord(id="a-1", username="inspe", role="admin")
    existing_workers = [
        UserRecord(id="u-1", username="anna", role="user", is_active=True),
        UserRecord(id="u-2", username="marek", role="user", is_active=True),
        UserRecord(id="u-3", username="piotr", role="user", is_active=True),
    ]

    mock_create = mocker.patch.object(AuthService, "create_user", return_value=UserRecord(id="u-4", username="kasia", role="user"))
    mock_pw = mocker.patch.object(AuthService, "update_user_password")
    mock_active = mocker.patch.object(AuthService, "set_user_active")
    mock_del = mocker.patch.object(AuthService, "delete_user")

    edited_rows = [
        {"Login": "anna", "Nowe hasło": "NoweHaslo123", "Aktywne": False, "Usuń": False},
        {"Login": "marek", "Nowe hasło": "", "Aktywne": True, "Usuń": True},
        # piotr removed via trash icon (omitted from edited_rows)
        {"Login": "kasia", "Nowe hasło": "Start123!", "Aktywne": True, "Usuń": False},
    ]

    stats = _apply_user_table_changes(admin, existing_workers, edited_rows)

    assert stats == {"created": 1, "updated": 1, "deleted": 2}
    mock_create.assert_called_once_with(admin, username="kasia", password="Start123!", role="user")
    mock_pw.assert_called_once_with(admin, "anna", "NoweHaslo123")
    mock_active.assert_called_once_with(admin, "anna", False)
    assert mock_del.call_count == 2

    with pytest.raises(ValueError, match="chronione"):
        _apply_user_table_changes(admin, existing_workers, [{"Login": "inspe", "Nowe hasło": "", "Aktywne": False, "Usuń": True}])


def test_should_create_and_verify_signed_session_token() -> None:
    import base64
    import json
    from src.auth.service import create_session_token, verify_session_token

    user = UserRecord(id="a-1", username="inspe", role="admin")
    token = create_session_token(user, ttl_seconds=600)

    assert token.count(".") == 1
    assert not any(ch in token for ch in "+/=")

    payload_b64, _ = token.split(".", 1)
    padded = payload_b64 + "=" * (-len(payload_b64) % 4)
    decoded_payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
    assert decoded_payload["sub"] == "a-1"
    assert decoded_payload["username"] == "inspe"
    assert decoded_payload["role"] == "admin"
    assert isinstance(decoded_payload["exp"], int)

    restored = verify_session_token(token)
    assert restored is not None
    assert restored.username == "inspe"
    assert restored.role == "admin"
    assert verify_session_token(token + "tamper") is None
    assert verify_session_token("invalid") is None
    assert verify_session_token(create_session_token(user, ttl_seconds=-10)) is None
