"""Tests del bucle del agente: rutas, guardarraíl y enlace tool_call_id."""

from __future__ import annotations

import json

import pytest

from src.rag_tools import agente
from src.rag_tools.agente import NO_EVIDENCIA, responder
from src.rag_tools.llm import _completion, _tool_call
from src.rag_tools.tools import Ejecutor
from src.rag_tools.vector_store import Buscador


@pytest.fixture()
def ejecutor(tmp_path):
    return Ejecutor(mock=True, buscador=Buscador(mock=True, directorio=tmp_path))


def test_ruta_funcion_mock(ejecutor):
    r = responder(
        "¿Cuántos puntos sumó el Betis en la temporada 2023/24?",
        mock=True,
        ejecutor=ejecutor,
    )
    assert r["ruta"] == "funcion"
    assert "19" in r["respuesta"]
    assert r["llamadas_llm"] == 2


def test_ruta_rag_mock(ejecutor):
    r = responder("¿Qué es una portería a cero?", mock=True, ejecutor=ejecutor)
    assert r["ruta"] == "rag"
    assert r["cita_ok"] is True
    assert any("porteria" in f for f in r["fuentes_recuperadas"])


def test_ruta_sin_evidencia_mundial(ejecutor):
    r = responder("¿Quién ganó el Mundial de 2010?", mock=True, ejecutor=ejecutor)
    assert r["ruta"] == "sin_evidencia"
    assert r["respuesta"] == NO_EVIDENCIA


def test_guardarrail_respuesta_sin_herramienta(monkeypatch, ejecutor):
    # El "modelo" contesta de memoria sin usar herramientas: se descarta.
    monkeypatch.setattr(agente, "llamar_con_tools", lambda *a, **k: _completion("Ganó España."))
    r = responder("¿Quién ganó el Mundial de 2010?", mock=True, ejecutor=ejecutor)
    assert r["respuesta"] == NO_EVIDENCIA
    assert r["traza"][-1]["guardarrail"] == "respuesta_sin_herramienta_descartada"


def test_mensaje_tool_enlazado_por_id(monkeypatch, ejecutor):
    vistos = []
    llamada = _tool_call("get_team_stats", {"team": "Betis", "season": "2023/24"})

    def falso_llm(messages, tools, **kwargs):
        vistos.append(list(messages))
        if messages[-1]["role"] == "user":
            return _completion(None, [llamada])
        return _completion("El Real Betis sumó 19 puntos (datos ficticios).")

    monkeypatch.setattr(agente, "llamar_con_tools", falso_llm)
    responder("¿Puntos del Betis en la 2023/24?", mock=True, ejecutor=ejecutor)
    segunda = vistos[1]
    assert segunda[-2]["role"] == "assistant" and segunda[-2]["tool_calls"][0]["id"] == llamada["id"]
    assert segunda[-1]["role"] == "tool" and segunda[-1]["tool_call_id"] == llamada["id"]
    assert json.loads(segunda[-1]["content"])["datos"]["puntos"] == 19


def test_max_vueltas_agotadas(monkeypatch, ejecutor):
    llamada = _tool_call("buscar_documentacion", {"consulta": "x" * 10})

    def siempre_tool(messages, tools, **kwargs):
        return _completion(None, [llamada])

    monkeypatch.setattr(agente, "llamar_con_tools", siempre_tool)
    # Forzar evidencia para no cortocircuitar por sin_evidencia.
    monkeypatch.setattr(ejecutor, "umbral", 99.0)
    r = responder("¿Qué es una portería a cero?", mock=True, ejecutor=ejecutor)
    assert r["respuesta"] == NO_EVIDENCIA
    assert r["llamadas_llm"] == 4
