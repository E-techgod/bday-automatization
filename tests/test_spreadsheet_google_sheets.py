from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.birthday_rules import parse_birthday
from app.config import Config
from app.spreadsheet.base import SpreadsheetError
from app.spreadsheet.google_sheets import GoogleSheetsProvider, _build_sheet_range


def test_google_sheets_load_rows_maps_headers_with_normalization() -> None:
    provider = GoogleSheetsProvider(
        config=_build_config(),
        service_factory=lambda: _FakeSheetsService(
            [
                [
                    " name ",
                    "EMAIL",
                    " birthday ",
                    "Ignored",
                    " last birthday email year ",
                ],
                ["Test Person", "test.person@example.com", "2000-01-02", "x", "2025"],
            ]
        ),
    )

    rows = provider.load_rows()

    assert rows == [
        {
            "Name": "Test Person",
            "Email": "test.person@example.com",
            "Birthday": "2000-01-02",
            "Last Birthday Email Year": "2025",
        }
    ]


def test_google_sheets_load_rows_raises_for_missing_required_header() -> None:
    provider = GoogleSheetsProvider(
        config=_build_config(),
        service_factory=lambda: _FakeSheetsService(
            [["Name", "Email"], ["Test Person", "test.person@example.com"]]
        ),
    )

    with pytest.raises(
        SpreadsheetError, match="Missing required spreadsheet header: Birthday"
    ):
        provider.load_rows()


def test_google_sheets_load_rows_raises_for_duplicate_normalized_headers() -> None:
    provider = GoogleSheetsProvider(
        config=_build_config(),
        service_factory=lambda: _FakeSheetsService(
            [
                ["Name", "Email", " email ", "Birthday"],
                ["Test Person", "one@example.com", "two@example.com", "2000-01-02"],
            ]
        ),
    )

    with pytest.raises(
        SpreadsheetError,
        match=r"Duplicate spreadsheet headers after normalization: 'Email', ' email '",
    ):
        provider.load_rows()


def test_google_sheets_load_rows_allows_missing_optional_last_sent_year() -> None:
    provider = GoogleSheetsProvider(
        config=_build_config(),
        service_factory=lambda: _FakeSheetsService(
            [
                ["Name", "Email", "Birthday"],
                ["Test Person", "test.person@example.com", "2000-01-02"],
            ]
        ),
    )

    rows = provider.load_rows()

    assert rows == [
        {
            "Name": "Test Person",
            "Email": "test.person@example.com",
            "Birthday": "2000-01-02",
        }
    ]


def test_google_sheets_load_rows_preserves_numeric_birthday_serial() -> None:
    provider = GoogleSheetsProvider(
        config=_build_config(),
        service_factory=lambda: _FakeSheetsService(
            [
                ["Name", "Email", "Birthday"],
                ["  Test Person  ", " test.person@example.com ", 36526],
            ]
        ),
    )

    rows = provider.load_rows()

    assert rows[0]["Name"] == "Test Person"
    assert rows[0]["Email"] == "test.person@example.com"
    assert isinstance(rows[0]["Birthday"], int | float)
    assert rows[0]["Birthday"] == 36526
    assert parse_birthday(rows[0]["Birthday"]) == date(2000, 1, 1)


def test_google_sheets_fetch_values_requests_unformatted_serialized_values() -> None:
    service = _FakeSheetsService(
        [
            ["Name", "Email", "Birthday"],
            ["Test Person", "test.person@example.com", 36527],
        ]
    )
    provider = GoogleSheetsProvider(
        config=_build_config(),
        service_factory=lambda: service,
    )

    provider.load_rows()

    assert service.last_get_kwargs == {
        "spreadsheetId": "test-sheet-id",
        "range": "Birthdays!A:ZZ",
        "valueRenderOption": "UNFORMATTED_VALUE",
        "dateTimeRenderOption": "SERIAL_NUMBER",
    }


def test_build_sheet_range_quotes_tab_names_with_spaces() -> None:
    config = _build_config(google_sheet_tab="Team Birthdays")

    assert _build_sheet_range(config) == "'Team Birthdays'!A:ZZ"


def test_build_sheet_range_escapes_apostrophes_in_tab_name() -> None:
    config = _build_config(google_sheet_tab="People's Birthdays")

    assert _build_sheet_range(config) == "'People''s Birthdays'!A:ZZ"


class _FakeSheetsService:
    def __init__(self, values: list[list[object]]) -> None:
        self._values = values
        self.last_get_kwargs: dict[str, object] | None = None

    def spreadsheets(self) -> _FakeSheetsService:
        return self

    def values(self) -> _FakeSheetsService:
        return self

    def get(self, **kwargs: object) -> _FakeSheetsRequest:
        self.last_get_kwargs = kwargs
        assert kwargs["spreadsheetId"] == "test-sheet-id"
        assert kwargs["range"] == "Birthdays!A:ZZ"
        return _FakeSheetsRequest(self._values)


class _FakeSheetsRequest:
    def __init__(self, values: list[list[object]]) -> None:
        self._values = values

    def execute(self) -> dict[str, list[list[object]]]:
        return {"values": self._values}


def _build_config(*, google_sheet_tab: str = "Birthdays") -> Config:
    return Config(
        app_timezone="America/Chicago",
        dry_run=True,
        test_date=None,
        spreadsheet_mode="google_sheet",
        google_sheet_id="test-sheet-id",
        google_sheet_tab=google_sheet_tab,
        google_drive_file_id="test-drive-id",
        name_column="Name",
        email_column="Email",
        birthday_column="Birthday",
        last_sent_year_column="Last Birthday Email Year",
        email_provider="gmail",
        email_from_name="Test Sender",
        email_from_address="sender@example.com",
        email_subject_template="Happy Birthday, {{name}}!",
        google_credentials_file=Path("synthetic-credentials.json"),
        google_impersonate_subject="sender@example.com",
        birthday_image_mode="none",
        birthday_image_path=Path("synthetic-banner.png"),
        birthday_image_url="",
        birthday_image_alt="Happy Birthday",
        birthday_image_width=600,
        state_db_path=Path("synthetic-state.db"),
        stale_claim_timeout_minutes=30,
        retry_max_attempts=3,
        retry_base_delay_seconds=1.0,
        log_level="INFO",
    )
