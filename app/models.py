from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Client:
    name: str
    email: str
    birthday: date
    row_index: int
    last_sent_year: int | None = None


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
