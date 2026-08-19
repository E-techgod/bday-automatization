from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.config import ConfigError, load_config


def test_load_config_valid_google_sheet_mode(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    image_path, credentials_path = _create_files(tmp_path)
    _set_base_env(monkeypatch, image_path, credentials_path)
    monkeypatch.setenv("SPREADSHEET_MODE", "google_sheet")
    monkeypatch.setenv("GOOGLE_SHEET_ID", "sheet-123")
    monkeypatch.setenv("GOOGLE_SHEET_TAB", "Birthdays")

    config = load_config()

    assert config.spreadsheet_mode == "google_sheet"
    assert config.google_sheet_id == "sheet-123"
    assert config.google_sheet_tab == "Birthdays"
    assert config.google_impersonate_subject == "sender@example.com"


def test_load_config_valid_xlsx_drive_mode(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    image_path, credentials_path = _create_files(tmp_path)
    _set_base_env(monkeypatch, image_path, credentials_path)
    monkeypatch.setenv("SPREADSHEET_MODE", "xlsx_drive")
    monkeypatch.setenv("GOOGLE_DRIVE_FILE_ID", "drive-123")

    config = load_config()

    assert config.spreadsheet_mode == "xlsx_drive"
    assert config.google_drive_file_id == "drive-123"


@pytest.mark.parametrize(
    ("mode", "missing_var"),
    [
        ("google_sheet", "GOOGLE_SHEET_ID"),
        ("xlsx_drive", "GOOGLE_DRIVE_FILE_ID"),
    ],
)
def test_load_config_missing_required_spreadsheet_id_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    mode: str,
    missing_var: str,
) -> None:
    image_path, credentials_path = _create_files(tmp_path)
    _set_base_env(monkeypatch, image_path, credentials_path)
    monkeypatch.setenv("SPREADSHEET_MODE", mode)
    monkeypatch.delenv(missing_var, raising=False)

    with pytest.raises(ConfigError):
        load_config()


def test_load_config_invalid_email_from_address_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    image_path, credentials_path = _create_files(tmp_path)
    _set_base_env(monkeypatch, image_path, credentials_path)
    monkeypatch.setenv("EMAIL_FROM_ADDRESS", "not-an-email")

    with pytest.raises(ConfigError):
        load_config()


def test_load_config_invalid_google_impersonate_subject_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    image_path, credentials_path = _create_files(tmp_path)
    _set_base_env(monkeypatch, image_path, credentials_path)
    monkeypatch.setenv("GOOGLE_IMPERSONATE_SUBJECT", "not-an-email")

    with pytest.raises(
        ConfigError,
        match="GOOGLE_IMPERSONATE_SUBJECT must be a valid email address",
    ):
        load_config()


def test_load_config_invalid_app_timezone_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    image_path, credentials_path = _create_files(tmp_path)
    _set_base_env(monkeypatch, image_path, credentials_path)
    monkeypatch.setenv("APP_TIMEZONE", "Not/ARealZone")

    with pytest.raises(
        ConfigError,
        match=r"APP_TIMEZONE is not a valid IANA timezone: 'Not/ARealZone'",
    ):
        load_config()


def test_load_config_valid_app_timezone_passes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    image_path, credentials_path = _create_files(tmp_path)
    _set_base_env(monkeypatch, image_path, credentials_path)
    monkeypatch.setenv("APP_TIMEZONE", "America/Chicago")

    config = load_config()

    assert config.app_timezone == "America/Chicago"


def test_load_config_missing_local_birthday_image_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    _, credentials_path = _create_files(tmp_path)
    missing_image_path = tmp_path / "missing.png"
    _set_base_env(monkeypatch, missing_image_path, credentials_path)

    with pytest.raises(ConfigError):
        load_config()


def test_load_config_without_birthday_image_mode_env_uses_none_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    _, credentials_path = _create_files(tmp_path)
    missing_image_path = tmp_path / "missing.png"
    _set_base_env(monkeypatch, missing_image_path, credentials_path)
    monkeypatch.delenv("BIRTHDAY_IMAGE_MODE", raising=False)

    config = load_config()

    assert config.birthday_image_mode == "none"
    assert config.birthday_image_path == missing_image_path


def test_load_config_invalid_email_provider_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    image_path, credentials_path = _create_files(tmp_path)
    _set_base_env(monkeypatch, image_path, credentials_path)
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")

    with pytest.raises(ConfigError):
        load_config()


def test_load_config_non_https_birthday_image_url_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    image_path, credentials_path = _create_files(tmp_path)
    _set_base_env(monkeypatch, image_path, credentials_path)
    monkeypatch.setenv("BIRTHDAY_IMAGE_MODE", "url")
    monkeypatch.setenv("BIRTHDAY_IMAGE_URL", "http://example.com/banner.png")

    with pytest.raises(ConfigError):
        load_config()


def test_load_config_non_positive_birthday_image_width_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    image_path, credentials_path = _create_files(tmp_path)
    _set_base_env(monkeypatch, image_path, credentials_path)
    monkeypatch.setenv("BIRTHDAY_IMAGE_WIDTH", "0")

    with pytest.raises(ConfigError):
        load_config()


def test_load_config_malformed_test_date_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    image_path, credentials_path = _create_files(tmp_path)
    _set_base_env(monkeypatch, image_path, credentials_path)
    monkeypatch.setenv("TEST_DATE", "2026-2-30")

    with pytest.raises(ConfigError):
        load_config()


def test_load_config_valid_test_date_parses_correctly(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    image_path, credentials_path = _create_files(tmp_path)
    _set_base_env(monkeypatch, image_path, credentials_path)
    monkeypatch.setenv("TEST_DATE", "2026-08-19")

    config = load_config()

    assert config.test_date == date(2026, 8, 19)


def test_load_config_invalid_dry_run_value_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    image_path, credentials_path = _create_files(tmp_path)
    _set_base_env(monkeypatch, image_path, credentials_path)
    monkeypatch.setenv("DRY_RUN", "yes")

    with pytest.raises(ConfigError):
        load_config()


def test_load_config_missing_google_credentials_file_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    image_path, _ = _create_files(tmp_path)
    missing_credentials = tmp_path / "missing-credentials.json"
    _set_base_env(monkeypatch, image_path, missing_credentials)

    with pytest.raises(ConfigError):
        load_config()


def test_load_config_succeeds_with_real_env_example_defaults(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    credentials_path = tmp_path / "credentials.json"
    credentials_path.write_text("{}", encoding="utf-8")

    for key in _parse_env_example():
        monkeypatch.delenv(key, raising=False)

    env_vars = _parse_env_example()
    env_vars.update(
        {
            "GOOGLE_SHEET_ID": "sheet-123",
            "EMAIL_FROM_ADDRESS": "sender@example.com",
            "GOOGLE_CREDENTIALS_FILE": str(credentials_path),
        }
    )

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    config = load_config()

    assert config.birthday_image_mode == "none"
    assert config.birthday_image_path == Path("app/assets/birthday_banner.png")
    assert config.email_provider == "gmail"


def _set_base_env(
    monkeypatch: pytest.MonkeyPatch,
    image_path,
    credentials_path,
) -> None:
    env_vars = {
        "APP_TIMEZONE": "America/Chicago",
        "DRY_RUN": "true",
        "TEST_DATE": "",
        "SPREADSHEET_MODE": "google_sheet",
        "GOOGLE_SHEET_ID": "sheet-123",
        "GOOGLE_SHEET_TAB": "",
        "GOOGLE_DRIVE_FILE_ID": "drive-123",
        "NAME_COLUMN": "Name",
        "EMAIL_COLUMN": "Email",
        "BIRTHDAY_COLUMN": "Birthday",
        "LAST_SENT_YEAR_COLUMN": "Last Birthday Email Year",
        "EMAIL_PROVIDER": "gmail",
        "EMAIL_FROM_NAME": "Sender Name",
        "EMAIL_FROM_ADDRESS": "sender@example.com",
        "EMAIL_SUBJECT_TEMPLATE": "Happy Birthday, {{name}}! 🎉",
        "GOOGLE_CREDENTIALS_FILE": str(credentials_path),
        "GOOGLE_IMPERSONATE_SUBJECT": "",
        "BIRTHDAY_IMAGE_MODE": "local",
        "BIRTHDAY_IMAGE_PATH": str(image_path),
        "BIRTHDAY_IMAGE_URL": "",
        "BIRTHDAY_IMAGE_ALT": "Happy Birthday",
        "BIRTHDAY_IMAGE_WIDTH": "600",
        "STATE_DB_PATH": "data/birthday_state.db",
        "STALE_CLAIM_TIMEOUT_MINUTES": "30",
        "RETRY_MAX_ATTEMPTS": "3",
        "RETRY_BASE_DELAY_SECONDS": "1.0",
        "LOG_LEVEL": "INFO",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)


def _create_files(tmp_path):
    image_path = tmp_path / "birthday_banner.png"
    image_path.write_bytes(b"png")
    credentials_path = tmp_path / "credentials.json"
    credentials_path.write_text("{}", encoding="utf-8")
    return image_path, credentials_path


def _parse_env_example() -> dict[str, str]:
    env_vars: dict[str, str] = {}
    for raw_line in Path(".env.example").read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env_vars[key.strip()] = value.strip()
    return env_vars
