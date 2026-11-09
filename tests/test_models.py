"""Tests del contrato Pydantic ExtraccionFutbol."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.models import ExtraccionFutbol


def test_normaliza_temporada_guion():
    m = ExtraccionFutbol.model_validate(
        {
            "equipo": "Real Betis",
            "temporada": "2023-2024",
            "metrica": "goles",
            "condicion": "local",
            "es_valida": True,
        }
    )
    assert m.temporada == "2023/24"
    assert m.equipo == "Real Betis"


def test_condicion_invalida_lanza():
    with pytest.raises(ValidationError):
        ExtraccionFutbol.model_validate(
            {
                "equipo": "Real Betis",
                "temporada": "2023/24",
                "metrica": "goles",
                "condicion": "en casa",
                "es_valida": True,
            }
        )


def test_error_semantico_permitido():
    m = ExtraccionFutbol.model_validate(
        {
            "equipo": "Málaga",
            "temporada": None,
            "metrica": "goles",
            "condicion": "local",
            "es_valida": False,
            "error": "falta_temporada",
        }
    )
    assert m.es_valida is False
    assert m.error == "falta_temporada"
