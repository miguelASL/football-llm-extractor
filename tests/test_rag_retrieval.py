"""Tests de troceado, Chroma mock y Ejecutor (sin descargas ni API)."""

from __future__ import annotations

import json

import pytest

from src.rag_tools.chunking import trocear_markdown
from src.rag_tools.tools import Ejecutor
from src.rag_tools.vector_store import Buscador, umbral_por_defecto


def test_trocear_entre_20_y_30_fragmentos():
    frags = trocear_markdown()
    assert 20 <= len(frags) <= 30
    ids = [f.id for f in frags]
    assert len(ids) == len(set(ids))
    assert frags[0].id == "diccionario_datos.md#tabla-partidos-ejemplo"
    assert "Puntos." in next(f.texto for f in frags if f.id.endswith("#puntos"))


def test_busqueda_top3_mock(tmp_path):
    b = Buscador(mock=True, directorio=tmp_path)
    resultados = b.buscar("¿Qué es una portería a cero?", k=3)
    assert len(resultados) == 3
    assert any("porteria-a-cero" in r.id for r in resultados)


def test_umbral_por_defecto_mock():
    assert umbral_por_defecto(True) == 0.60


def test_ejecutor_stats_ok(tmp_path):
    ej = Ejecutor(mock=True, buscador=Buscador(mock=True, directorio=tmp_path))
    r = ej.ejecutar("get_team_stats", json.dumps({"team": "Betis", "season": "2023/24"}))
    assert r["ok"] is True
    assert r["datos"]["puntos"] == 19


def test_ejecutor_equipo_invalido_no_ejecuta(tmp_path):
    ej = Ejecutor(mock=True, buscador=Buscador(mock=True, directorio=tmp_path))
    r = ej.ejecutar("get_team_stats", json.dumps({"team": "Atlético", "season": "2023/24"}))
    assert r["ok"] is False
    assert r["error"] == "argumentos_invalidos"
    assert any(e["campo"] == "team" for e in r["detalle"])


def test_ejecutar_rag_conceptual(tmp_path):
    ej = Ejecutor(mock=True, buscador=Buscador(mock=True, directorio=tmp_path))
    r = ej.ejecutar(
        "buscar_documentacion",
        json.dumps({"consulta": "¿Qué es una portería a cero?"}),
    )
    assert r["ok"] is True
    if not r.get("sin_evidencia"):
        assert any("porteria" in f["fuente"] for f in r["fragmentos"])
