from __future__ import annotations

from datetime import date

import pytest

from app.models import Client, resolve_salutation


@pytest.mark.parametrize(
    "gender",
    ["Mujer", "Femenino", "F", "Female"],
)
def test_resolve_salutation_female_values_map_to_estimada(gender: str) -> None:
    assert resolve_salutation(gender) == "Estimada"


@pytest.mark.parametrize(
    "gender",
    ["Hombre", "Masculino", "M", "Male"],
)
def test_resolve_salutation_male_values_map_to_estimado(gender: str) -> None:
    assert resolve_salutation(gender) == "Estimado"


def test_resolve_salutation_missing_gender_defaults_to_estimado_a() -> None:
    assert resolve_salutation(None) == "Estimado/a"


def test_resolve_salutation_empty_gender_defaults_to_estimado_a() -> None:
    assert resolve_salutation("") == "Estimado/a"


def test_resolve_salutation_unknown_gender_defaults_to_estimado_a() -> None:
    assert resolve_salutation("Nonbinary") == "Estimado/a"


@pytest.mark.parametrize(
    ("gender", "expected"),
    [
        ("mujer", "Estimada"),
        ("MUJER", "Estimada"),
        ("MuJeR", "Estimada"),
        ("male", "Estimado"),
        ("MALE", "Estimado"),
        ("MaLe", "Estimado"),
    ],
)
def test_resolve_salutation_is_case_insensitive(gender: str, expected: str) -> None:
    assert resolve_salutation(gender) == expected


@pytest.mark.parametrize(
    ("gender", "expected"),
    [
        ("  Mujer  ", "Estimada"),
        ("\tFemale\n", "Estimada"),
        ("  Hombre  ", "Estimado"),
        ("\tMale\n", "Estimado"),
        ("   ", "Estimado/a"),
    ],
)
def test_resolve_salutation_strips_surrounding_whitespace(
    gender: str, expected: str
) -> None:
    assert resolve_salutation(gender) == expected


def test_client_salutation_property_reflects_gender() -> None:
    client = Client(
        name="Test",
        email="test@example.com",
        birthday=date(2000, 1, 1),
        row_index=2,
        gender="Femenino",
    )

    assert client.salutation == "Estimada"


def test_client_salutation_property_defaults_when_gender_missing() -> None:
    client = Client(
        name="Test",
        email="test@example.com",
        birthday=date(2000, 1, 1),
        row_index=2,
    )

    assert client.salutation == "Estimado/a"
