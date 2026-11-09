"""Tests de la tubería con --mock (sin API)."""

from __future__ import annotations

from src.extractor import extraer, limpiar_fences


def test_limpiar_fences():
    raw = '```json\n{"a": 1}\n```'
    assert limpiar_fences(raw) == '{"a": 1}'


def test_extraer_caso_completo_mock():
    r = extraer(
        "¿Cuántos goles marcó el Betis en casa en la 2023/24?",
        tipo_prompt="claro",
        mock=True,
    )
    assert r["parse_ok"] is True
    assert r["validacion_ok"] is True
    assert r["datos"]["equipo"] == "Real Betis"
    assert r["datos"]["es_valida"] is True


def test_extraer_sin_temporada_mock():
    r = extraer(
        "¿Cuántos goles marcó el Málaga en casa?",
        tipo_prompt="claro",
        mock=True,
    )
    assert r["datos"]["es_valida"] is False
    assert r["datos"]["error"] == "falta_temporada"


def test_extraer_no_futbol_mock():
    r = extraer("¿Quién inventó la bombilla?", tipo_prompt="claro", mock=True)
    assert r["datos"]["error"] == "no_futbolistica"


def test_fila_resultado_tolera_lista():
    from src.evaluate import fila_resultado

    fila = fila_resultado(
        "1",
        "nota",
        "vago",
        {
            "pregunta": "x",
            "parse_ok": True,
            "validacion_ok": False,
            "datos": [{"equipo": "Betis"}],
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "total_tokens": 2,
            "latencia_ms": 1,
            "error_parseo": None,
            "error_validacion": "lista",
        },
    )
    assert fila["es_valida"] is None
    assert fila["equipo"] is None

