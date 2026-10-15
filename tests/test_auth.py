
# File: D:\Technative\ai-jobmatch-agent\tests\test_auth.py

"""Tests for the local single-user authentication module."""

from datetime import datetime, timedelta, timezone

import pytest

from auth import (
    authenticate,
    create_password,
    initialize_auth,
    is_password_configured,
    lockout_remaining_seconds,
)
from database import connect


@pytest.fixture
def auth_db(tmp_path):
    """Give every test an isolated temporary database."""
    path = tmp_path / "auth-test.db"
    initialize_auth(path)
    return path


def test_first_run_has_no_configured_password(auth_db):
    assert is_password_configured(auth_db) is False

    success, message = authenticate("anything", auth_db)

    assert success is False
    assert "not been set up" in message.lower()


def test_password_is_hashed_and_can_be_verified(auth_db):
    password = "Correct-Horse-Battery-42!"

    create_password(password, password, auth_db)

    assert is_password_configured(auth_db) is True

    conn = connect(auth_db)
    try:
        row = conn.execute(
            "SELECT password_hash FROM auth_user WHERE id = 1"
        ).fetchone()
        stored_hash = row["password_hash"]
    finally:
        conn.close()

    assert stored_hash != password
    assert stored_hash.startswith("$argon2id$")

    success, message = authenticate(password, auth_db)

    assert success is True
    assert "success" in message.lower()


def test_password_setup_rejects_short_password(auth_db):
    with pytest.raises(ValueError, match="at least 12"):
        create_password("short", "short", auth_db)

    assert is_password_configured(auth_db) is False


def test_password_setup_rejects_mismatched_confirmation(auth_db):
    with pytest.raises(ValueError, match="do not match"):
        create_password(
            "Long-Enough-Password",
            "Different-Password",
            auth_db,
        )

    assert is_password_configured(auth_db) is False


def test_password_cannot_be_reset_by_running_setup_again(auth_db):
    original = "Initial-Password-123!"
    replacement = "Replacement-Password-456!"

    create_password(original, original, auth_db)

    with pytest.raises(ValueError, match="already been configured"):
        create_password(replacement, replacement, auth_db)

    success, _ = authenticate(original, auth_db)
    assert success is True


def test_failed_attempts_trigger_lockout(auth_db):
    password = "Correct-Horse-Battery-42!"
    create_password(password, password, auth_db)

    for _ in range(4):
        success, message = authenticate("wrong-password", auth_db)
        assert success is False
        assert message == "Incorrect password."

    success, message = authenticate("wrong-password", auth_db)

    assert success is False
    assert "too many failed attempts" in message.lower()
    assert lockout_remaining_seconds(auth_db) > 0

    success, message = authenticate(password, auth_db)

    assert success is False
    assert "too many failed attempts" in message.lower()


def test_expired_lockout_allows_login_again(auth_db):
    password = "Correct-Horse-Battery-42!"
    create_password(password, password, auth_db)

    for _ in range(5):
        authenticate("wrong-password", auth_db)

    expired = (
        datetime.now(timezone.utc) - timedelta(seconds=5)
    ).isoformat()

    conn = connect(auth_db)
    try:
        conn.execute(
            "UPDATE auth_login_attempts SET locked_until = ? WHERE id = 1",
            (expired,),
        )
        conn.commit()
    finally:
        conn.close()

    success, _ = authenticate(password, auth_db)

    assert success is True
    assert lockout_remaining_seconds(auth_db) == 0


def test_successful_login_clears_failed_attempts(auth_db):
    password = "Correct-Horse-Battery-42!"
    create_password(password, password, auth_db)

    authenticate("wrong-password", auth_db)
    authenticate("wrong-password", auth_db)

    success, _ = authenticate(password, auth_db)
    assert success is True

    conn = connect(auth_db)
    try:
        row = conn.execute(
            """
            SELECT failed_attempts, locked_until
            FROM auth_login_attempts
            WHERE id = 1
            """
        ).fetchone()
    finally:
        conn.close()

    assert row["failed_attempts"] == 0
    assert row["locked_until"] is None
