"""Orquestación: prompt → LLM → JSON → validación Pydantic."""

from __future__ import annotations

import json
import re
import time
from typing import Any, Optional

from pydantic import ValidationError

from src.models import ExtraccionFutbol
from src.prompts import construir_mensajes

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


def limpiar_fences(texto: str) -> str:
    """Quita fences markdown ```json ... ``` si el modelo las envuelve."""
    limpio = texto.strip()
    if limpio.startswith("```"):
        limpio = _FENCE_RE.sub("", limpio).strip()
    return limpio


def respuesta_mock(pregunta: str) -> dict[str, Any]:
    """Simula una respuesta del LLM sin consumir cuota."""
    q = pregunta.lower()
    if "bombilla" in q or "inventó" in q:
        datos = {
            "equipo": None,
            "temporada": None,
            "metrica": None,
            "condicion": None,
            "es_valida": False,
            "error": "no_futbolistica",
        }
    elif "pacheta" in q:
        datos = {
            "equipo": None,
            "temporada": "2023/24",
            "metrica": "puntos",
            "condicion": "global",
            "es_valida": False,
            "error": "equipo_ambiguo",
        }
    elif "pedri" in q:
        datos = {
            "equipo": "FC Barcelona",
            "temporada": "2022/23",
            "metrica": "asistencias",
            "condicion": "global",
            "es_valida": False,
            "error": "jugador_no_equipo",
        }
    elif "málaga" in q or "malaga" in q:
        datos = {
            "equipo": "Málaga",
            "temporada": None,
            "metrica": "goles",
            "condicion": "local",
            "es_valida": False,
            "error": "falta_temporada",
        }
    elif "betis" in q and "2023" in q:
        datos = {
            "equipo": "Real Betis",
            "temporada": "2023/24",
            "metrica": "goles",
            "condicion": "local",
            "es_valida": True,
            "error": None,
        }
    else:
        datos = {
            "equipo": "Real Madrid" if "madrid" in q else "Desconocido",
            "temporada": "2023/24" if "2023" in q else None,
            "metrica": "goles",
            "condicion": "visitante" if "fuera" in q or "visitante" in q else "local",
            "es_valida": "2023" in q or "2022" in q or "2021" in q or "2020" in q or "2019" in q,
            "error": None if ("2023" in q or "2022" in q or "2021" in q) else "falta_temporada",
        }
        if not datos["es_valida"] and datos["error"] is None:
            datos["error"] = "falta_temporada"

    return {
        "content": json.dumps(datos, ensure_ascii=False),
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }


def extraer(
    pregunta: str,
    *,
    tipo_prompt: str = "claro",
    mock: bool = False,
) -> dict[str, Any]:
    """Ejecuta la tubería completa y devuelve un dict serializable."""
    messages = construir_mensajes(pregunta, tipo_prompt)
    t0 = time.perf_counter()

    raw_content: Optional[str] = None
    usage: dict[str, Any] = {}

    if mock:
        mock_resp = respuesta_mock(pregunta)
        raw_content = mock_resp["content"]
        usage = mock_resp["usage"]
    else:
        from src.client import llamar_chat

        resp = llamar_chat(messages)
        raw_content = resp.choices[0].message.content or ""
        if resp.usage is not None:
            usage = {
                "prompt_tokens": resp.usage.prompt_tokens,
                "completion_tokens": resp.usage.completion_tokens,
                "total_tokens": resp.usage.total_tokens,
            }

    latencia_ms = round((time.perf_counter() - t0) * 1000, 2)

    resultado: dict[str, Any] = {
        "pregunta": pregunta,
        "tipo_prompt": tipo_prompt,
        "parse_ok": False,
        "validacion_ok": False,
        "datos": None,
        "error_parseo": None,
        "error_validacion": None,
        "latencia_ms": latencia_ms,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "raw_content": raw_content,
    }

    try:
        payload = json.loads(limpiar_fences(raw_content or ""))
        resultado["parse_ok"] = True
    except json.JSONDecodeError as exc:
        resultado["error_parseo"] = str(exc)
        return resultado

    try:
        modelo = ExtraccionFutbol.model_validate(payload)
        resultado["validacion_ok"] = True
        resultado["datos"] = modelo.model_dump(mode="json")
    except ValidationError as exc:
        resultado["error_validacion"] = exc.errors()
        resultado["datos"] = payload

    return resultado
