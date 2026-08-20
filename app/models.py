from __future__ import annotations

from dataclasses import dataclass
from datetime import date


def build_display_name(first_name: str, last_name: str | None) -> str:
    normalized_first = _normalize_name_part(first_name)
    normalized_last = _normalize_name_part(last_name) if last_name else ""
    if not normalized_last:
        return normalized_first
    return f"{normalized_first} {normalized_last}"


def _normalize_name_part(value: str) -> str:
    return " ".join(value.split())


@dataclass(frozen=True)
class Client:
    name: str
    email: str
    birthday: date
    row_index: int
    last_sent_year: int | None = None
    last_name: str | None = None

    @property
    def display_name(self) -> str:
        return build_display_name(self.name, self.last_name)


@dataclass(frozen=True)
class BirthdayMatch:
    client: Client
    celebrated_year: int


@dataclass(frozen=True)
class SendResult:
    client: Client
    celebrated_year: int
    success: bool
    error_message: str | None = None
