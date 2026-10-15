
# File: D:\Technative\ai-jobmatch-agent\auth.py

"""Single-user authentication for the local Streamlit application.

Passwords are hashed with Argon2id. Failed attempts are stored in SQLite so
restarting the application does not reset the lockout.

This module is intended for a local application. Streamlit session state is
not a security boundary for applications exposed to a network.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import streamlit as st
from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

from database import connect


_PASSWORD_HASHER = PasswordHasher()
_MIN_PASSWORD_LENGTH = 12
_MAX_PASSWORD_LENGTH = 1024
_MAX_FAILED_ATTEMPTS = 5
_ATTEMPT_WINDOW = timedelta(minutes=15)
_LOCKOUT_DURATION = timedelta(minutes=15)


def _utc_now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    """Serialize a datetime consistently in UTC."""
    return value.astimezone(timezone.utc).isoformat()


def _parse_timestamp(value: str | None) -> datetime | None:
    """Parse a stored timestamp, tolerating legacy naive timestamps."""
    if not value:
        return None

    parsed = datetime.fromisoformat(value)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def initialize_auth(path: Path | str | None = None) -> None:
    """Create authentication tables without modifying existing app tables."""
    conn = connect(path)

    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS auth_user (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS auth_login_attempts (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                window_started_at TEXT,
                locked_until TEXT
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def is_password_configured(path: Path | str | None = None) -> bool:
    """Return whether the single local account has a configured password."""
    initialize_auth(path)
    conn = connect(path)

    try:
        row = conn.execute(
            "SELECT 1 FROM auth_user WHERE id = 1"
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def create_password(
    password: str,
    confirm_password: str | None = None,
    path: Path | str | None = None,
) -> None:
    """Create the first password; never overwrite an existing password."""
    if not isinstance(password, str):
        raise ValueError("Password must be text.")

    if len(password) < _MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Use a password of at least {_MIN_PASSWORD_LENGTH} characters."
        )

    if len(password) > _MAX_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be no longer than {_MAX_PASSWORD_LENGTH} characters."
        )

    if confirm_password is not None and password != confirm_password:
        raise ValueError("The passwords do not match.")

    initialize_auth(path)

    password_hash = _PASSWORD_HASHER.hash(password)
    now = _timestamp(_utc_now())
    conn = connect(path)

    try:
        conn.execute("BEGIN IMMEDIATE")

        existing = conn.execute(
            "SELECT 1 FROM auth_user WHERE id = 1"
        ).fetchone()

        if existing is not None:
            conn.rollback()
            raise ValueError("A password has already been configured.")

        conn.execute(
            """
            INSERT INTO auth_user (
                id, password_hash, created_at, updated_at
            )
            VALUES (1, ?, ?, ?)
            """,
            (password_hash, now, now),
        )

        conn.execute(
            """
            INSERT OR IGNORE INTO auth_login_attempts (
                id, failed_attempts, window_started_at, locked_until
            )
            VALUES (1, 0, NULL, NULL)
            """
        )

        conn.commit()

    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        conn.close()


def lockout_remaining_seconds(
    path: Path | str | None = None,
) -> int:
    """Return remaining lockout seconds, or zero when not locked."""
    initialize_auth(path)
    conn = connect(path)

    try:
        row = conn.execute(
            "SELECT locked_until FROM auth_login_attempts WHERE id = 1"
        ).fetchone()

        locked_until = _parse_timestamp(row["locked_until"]) if row else None

        if locked_until is None:
            return 0

        remaining = (locked_until - _utc_now()).total_seconds()
        return max(0, int(remaining + 0.999))

    finally:
        conn.close()


def authenticate(
    password: str,
    path: Path | str | None = None,
) -> tuple[bool, str]:
    """Verify a password and enforce persistent failed-login limits.

    Five failures within a 15-minute window trigger a 15-minute lockout.
    Successful authentication resets the failure counter.
    """
    initialize_auth(path)

    now = _utc_now()
    conn = connect(path)

    try:
        # Serialize login attempts so concurrent requests cannot bypass limits.
        conn.execute("BEGIN IMMEDIATE")

        user = conn.execute(
            "SELECT password_hash FROM auth_user WHERE id = 1"
        ).fetchone()

        if user is None:
            conn.rollback()
            return False, "Password has not been set up yet."

        attempt = conn.execute(
            """
            SELECT failed_attempts, window_started_at, locked_until
            FROM auth_login_attempts
            WHERE id = 1
            """
        ).fetchone()

        failed_attempts = int(attempt["failed_attempts"]) if attempt else 0
        window_started_at = (
            _parse_timestamp(attempt["window_started_at"])
            if attempt
            else None
        )
        locked_until = (
            _parse_timestamp(attempt["locked_until"])
            if attempt
            else None
        )

        if locked_until is not None and locked_until > now:
            seconds = max(
                1,
                int((locked_until - now).total_seconds() + 0.999),
            )
            conn.rollback()
            minutes = max(1, (seconds + 59) // 60)

            return (
                False,
                f"Too many failed attempts. Try again in about "
                f"{minutes} minute(s).",
            )

        if (
            locked_until is not None
            or window_started_at is None
            or now - window_started_at >= _ATTEMPT_WINDOW
        ):
            failed_attempts = 0
            window_started_at = now

            conn.execute(
                """
                INSERT INTO auth_login_attempts (
                    id, failed_attempts, window_started_at, locked_until
                )
                VALUES (1, 0, ?, NULL)
                ON CONFLICT(id) DO UPDATE SET
                    failed_attempts = 0,
                    window_started_at = excluded.window_started_at,
                    locked_until = NULL
                """,
                (_timestamp(window_started_at),),
            )

        try:
            _PASSWORD_HASHER.verify(user["password_hash"], password)

        except (
            VerifyMismatchError,
            VerificationError,
            InvalidHashError,
            TypeError,
        ):
            failed_attempts += 1

            new_lockout = (
                _timestamp(now + _LOCKOUT_DURATION)
                if failed_attempts >= _MAX_FAILED_ATTEMPTS
                else None
            )

            conn.execute(
                """
                INSERT INTO auth_login_attempts (
                    id, failed_attempts, window_started_at, locked_until
                )
                VALUES (1, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    failed_attempts = excluded.failed_attempts,
                    window_started_at = excluded.window_started_at,
                    locked_until = excluded.locked_until
                """,
                (
                    failed_attempts,
                    _timestamp(window_started_at or now),
                    new_lockout,
                ),
            )

            conn.commit()

            if new_lockout is not None:
                return (
                    False,
                    "Too many failed attempts. Try again in about 15 minute(s).",
                )

            return False, "Incorrect password."

        conn.execute(
            """
            INSERT INTO auth_login_attempts (
                id, failed_attempts, window_started_at, locked_until
            )
            VALUES (1, 0, NULL, NULL)
            ON CONFLICT(id) DO UPDATE SET
                failed_attempts = 0,
                window_started_at = NULL,
                locked_until = NULL
            """
        )

        conn.commit()
        return True, "Signed in successfully."

    except sqlite3.Error:
        conn.rollback()
        raise

    finally:
        conn.close()


def render_auth_gate(path: Path | str | None = None) -> bool:
    """Render first-run setup or login and return True when authenticated."""
    initialize_auth(path)

    if st.session_state.get("auth_authenticated") is True:
        with st.sidebar:
            st.caption("Signed in to the local application.")

            if st.button("Log out", key="auth_logout_button"):
                st.session_state["auth_authenticated"] = False
                st.rerun()

        return True

    st.title("AI JobMatch Agent")
    st.caption("Local-first CV profiling and explainable job matching")

    if not is_password_configured(path):
        st.subheader("Set up your password")
        st.info(
            "First run: create a password of at least 12 characters. "
            "Only an Argon2 password hash will be stored."
        )

        with st.form("auth_setup_form"):
            password = st.text_input(
                "Create password",
                type="password",
            )
            confirmation = st.text_input(
                "Confirm password",
                type="password",
            )
            submitted = st.form_submit_button("Set password and sign in")

        if submitted:
            try:
                create_password(password, confirmation, path)

            except ValueError as exc:
                st.error(str(exc))

            except Exception:
                st.error(
                    "Password setup failed. Check the application log "
                    "and try again."
                )

            else:
                st.session_state["auth_authenticated"] = True
                st.rerun()

        return False

    st.subheader("Sign in")

    with st.form("auth_login_form"):
        password = st.text_input(
            "Password",
            type="password",
        )
        submitted = st.form_submit_button("Sign in")

    if submitted:
        try:
            success, message = authenticate(password, path)

        except Exception:
            st.error(
                "Sign-in failed due to a local database error. "
                "Check the application log."
            )
            return False

        if success:
            st.session_state["auth_authenticated"] = True
            st.rerun()

        st.error(message)

    return False
