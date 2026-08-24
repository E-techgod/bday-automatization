from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Config
from app.spreadsheet.base import SpreadsheetError, resolve_headers


def test_resolve_headers_raises_for_colliding_configured_columns() -> None:
    config = _build_config(birthday_column=" email ")

    with pytest.raises(
        SpreadsheetError,
        match=r"Configured spreadsheet columns collide after normalization: 'Email' and ' email '",
    ):
        resolve_headers(["Name", "Email", "Birthday"], config)


def test_resolve_headers_includes_last_name_when_present() -> None:
    config = _build_config()

    resolved = resolve_headers(["Name", "Last Name", "Email", "Birthday"], config)

    assert resolved["Last Name"] == 1


def test_resolve_headers_omits_last_name_when_absent() -> None:
    config = _build_config()

    resolved = resolve_headers(["Name", "Email", "Birthday"], config)

    assert "Last Name" not in resolved


def test_resolve_headers_includes_gender_when_present() -> None:
    config = _build_config()

    resolved = resolve_headers(["Name", "Gender", "Email", "Birthday"], config)

    assert resolved["Gender"] == 1


def test_resolve_headers_omits_gender_when_absent() -> None:
    config = _build_config()

    resolved = resolve_headers(["Name", "Email", "Birthday"], config)

    assert "Gender" not in resolved


def _build_config(*, birthday_column: str = "Birthday") -> Config:
    return Config(
        app_timezone="America/Chicago",
        dry_run=True,
        test_date=None,
        spreadsheet_mode="google_sheet",
        google_sheet_id="test-sheet-id",
        google_sheet_tab="Birthdays",
        google_drive_file_id="test-drive-id",
        name_column="Name",
        last_name_column="Last Name",
        gender_column="Gender",
        email_column="Email",
        birthday_column=birthday_column,
        last_sent_year_column="Last Birthday Email Year",
        email_provider="gmail",
        email_from_name="Test Sender",
        email_from_address="sender@example.com",
        email_subject_template="Happy Birthday, {{name}}!",
        google_auth_mode="service_account",
        google_credentials_file=Path("synthetic-credentials.json"),
        google_impersonate_subject="sender@example.com",
        google_oauth_client_secrets_file=None,
        google_oauth_token_file=Path("synthetic-oauth-token.json"),
        birthday_image_mode="none",
        birthday_image_path=Path("synthetic-banner.png"),
        birthday_image_url="",
        birthday_image_alt="Happy Birthday",
        birthday_image_width=600,
        state_backend="sqlite",
        state_db_path=Path("synthetic-state.db"),
        firestore_database="birthday-automation",
        stale_claim_timeout_minutes=30,
        retry_max_attempts=3,
        retry_base_delay_seconds=1.0,
        log_level="INFO",
    )
