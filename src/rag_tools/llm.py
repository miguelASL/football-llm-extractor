"""Llamada al LLM con tools (API real) y mock offline para tests / --mock."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from openai import APIConnectionError, APITimeoutError, RateLimitError
from openai.types.chat import ChatCompletion
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

_EQUIPO_RE = re.compile(
    r"\b(betis|sevilla|m[aá]laga|madrid|bar(?:ç|c)?a|barcelona|athletic)\b",
    re.IGNORECASE,
)
_TEMPORADA_RE = re.compile(r"(20\d{2})\s*[/\-]\s*(20\d{2}|\d{2})")
_LOCAL_RE = re.compile(r"\b(casa|local|en casa)\b", re.IGNORECASE)
_VISITANTE_RE = re.compile(r"\b(fuera|visitante|fuera de casa)\b", re.IGNORECASE)


def _usage(prompt: int = 50, completion: int = 20) -> dict[str, int]:
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
    }


def _tool_call(name: str, arguments: dict[str, Any], call_id: str | None = None) -> dict[str, Any]:
    return {
        "id": call_id or f"call_{uuid.uuid4().hex[:12]}",
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments, ensure_ascii=False)},
    }


def _completion(
    content: str | None,
    tool_calls: list[dict[str, Any]] | None = None,
    usage: dict[str, int] | None = None,
) -> ChatCompletion:
    """Construye un ChatCompletion auténtico del SDK (el bucle del agente es el mismo)."""
    u = usage or _usage()
    payload: dict[str, Any] = {
        "id": f"chatcmpl-mock-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": 0,
        "model": "mock",
        "choices": [
            {
                "index": 0,
                "finish_reason": "tool_calls" if tool_calls else "stop",
                "message": {
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls,
                },
            }
        ],
        "usage": u,
    }
    return ChatCompletion.model_validate(payload)


def _detectar_condicion(pregunta: str) -> str:
    if _VISITANTE_RE.search(pregunta):
        return "visitante"
    if _LOCAL_RE.search(pregunta):
        return "local"
    return "global"


def _detectar_equipo(pregunta: str) -> str | None:
    m = _EQUIPO_RE.search(pregunta)
    return m.group(1) if m else None


def _detectar_temporada(pregunta: str) -> str | None:
    m = _TEMPORADA_RE.search(pregunta)
    if not m:
        return None
    a, b = m.group(1), m.group(2)
    return f"{a}/{b[-2:]}"


def respuesta_mock(messages: list[dict[str, Any]]) -> ChatCompletion:
    """Simula el router: 1.ª vuelta pide tool; 2.ª redacta con el resultado."""
    ultimo = messages[-1]
    # Segunda vuelta: ya hay resultado de herramienta.
    if ultimo.get("role") == "tool":
        try:
            resultado = json.loads(ultimo.get("content") or "{}")
        except json.JSONDecodeError:
            resultado = {}
        if resultado.get("sin_evidencia"):
            return _completion(
                "No dispongo de evidencia en mis documentos para responder a eso."
            )
        if resultado.get("ok") and "datos" in resultado:
            d = resultado["datos"]
            return _completion(
                f"Según get_team_stats (datos ficticios), {d['team']} registró "
                f"{d['puntos']} puntos, {d['victorias']} victorias, {d['empates']} empates, "
                f"{d['derrotas']} derrotas, {d['goles_favor']} goles a favor y "
                f"{d['goles_contra']} goles en contra en la temporada {d['season']} "
                f"(condición: {d['condicion']})."
            )
        if resultado.get("ok") and resultado.get("fragmentos"):
            frag = resultado["fragmentos"][0]
            return _completion(
                f"Según la documentación: {frag['texto'][:220]} [{frag['fuente']}]"
            )
        if not resultado.get("ok"):
            detalle = resultado.get("detalle", resultado.get("error", "error"))
            return _completion(f"No pude completar la consulta: {detalle}")
        return _completion(
            "No dispongo de evidencia en mis documentos para responder a eso."
        )

    # Primera vuelta: mirar la pregunta del usuario.
    pregunta = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            pregunta = m.get("content") or ""
            break

    equipo = _detectar_equipo(pregunta)
    temporada = _detectar_temporada(pregunta)
    if equipo and temporada:
        return _completion(
            None,
            [
                _tool_call(
                    "get_team_stats",
                    {
                        "team": equipo,
                        "season": temporada,
                        "condicion": _detectar_condicion(pregunta),
                    },
                )
            ],
        )

    # Conceptual o fuera de corpus: el mock pide RAG; el umbral decide evidencia.
    return _completion(
        None,
        [_tool_call("buscar_documentacion", {"consulta": pregunta})],
    )


def llamar_con_tools(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    *,
    mock: bool = False,
    tool_choice: str = "auto",
) -> ChatCompletion:
    """Igual que en la semana 1, pero SIN response_format: aquí el modelo responde con tool_calls."""
    if mock:
        return respuesta_mock(messages)

    from src.client import crear_cliente  # reutiliza el cliente de la semana 1
    from src.config import get_settings

    cfg = get_settings()
    cliente = crear_cliente(cfg)

    @retry(
        stop=stop_after_attempt(cfg.max_retries),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIConnectionError)),
        reraise=True,
    )
    def _llamar() -> ChatCompletion:
        return cliente.chat.completions.create(
            model=cfg.model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=0,
        )

    return _llamar()
