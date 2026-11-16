"""El bucle completo: pregunta -> el modelo elige herramienta -> su código valida y ejecuta
-> mensaje role='tool' -> respuesta final con cifras o con fuentes citadas."""

from __future__ import annotations

import argparse
import json
import re
import time
from typing import Any

from src.rag_tools.llm import llamar_con_tools
from src.rag_tools.tools import TOOLS, Ejecutor

NO_EVIDENCIA = "No dispongo de evidencia en mis documentos para responder a eso."
MAX_VUELTAS = 4  # tope de idas y vueltas: evita bucles infinitos si el modelo se empeña

SYSTEM = f"""Eres el asistente de un proyecto de datos de fútbol. Respondes en español, en una o dos frases.
Reglas:
1. Toda cifra (goles, puntos, victorias...) sale de la herramienta get_team_stats. Nunca calcules ni recuerdes cifras de memoria.
2. Para definiciones, reglas de cálculo o limitaciones usa buscar_documentacion y cita cada fuente usada entre corchetes, p. ej. [diccionario_datos.md#puntos].
3. Si la pregunta no trata de estos datos, responde exactamente: "{NO_EVIDENCIA}"
4. Si get_team_stats devuelve datos, indica que son datos ficticios de ejemplo."""

_CITA_RE = re.compile(r"\[([^\[\]]+?\.md#[a-z0-9-]+)\]")


def _serializar_tool_call(tc: Any) -> dict[str, Any]:
    """Reenvía el tool_call al historial, conservando extra_content (thought_signature de Gemini)."""
    item: dict[str, Any] = {
        "id": tc.id,
        "type": "function",
        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
    }
    extra = getattr(tc, "extra_content", None)
    if extra is not None:
        if hasattr(extra, "model_dump"):
            item["extra_content"] = extra.model_dump(exclude_none=True)
        elif isinstance(extra, dict):
            item["extra_content"] = extra
    return item


def responder(pregunta: str, *, mock: bool = False, ejecutor: Ejecutor | None = None) -> dict[str, Any]:
    ejecutor = ejecutor or Ejecutor(mock=mock)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": pregunta},
    ]
    traza: list[dict[str, Any]] = []
    fuentes: list[str] = []
    tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    llamadas_llm = 0
    respuesta: str | None = None
    ruta = "sin_evidencia"
    t0 = time.perf_counter()

    for _ in range(MAX_VUELTAS):
        completion = llamar_con_tools(messages, TOOLS, mock=mock)
        llamadas_llm += 1
        if completion.usage:
            for k in tokens:
                tokens[k] += getattr(completion.usage, k) or 0
        msg = completion.choices[0].message

        if not msg.tool_calls:  # el modelo ya no pide herramientas: es la respuesta final
            respuesta = (msg.content or "").strip()
            break

        # Paso clave: devolver al historial el mensaje del asistente CON sus tool_calls...
        # (incluye thought_signature de Gemini si viene en extra_content)
        messages.append(
            {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [_serializar_tool_call(tc) for tc in msg.tool_calls],
            }
        )
        sin_evidencia = False
        for tc in msg.tool_calls:
            resultado = ejecutor.ejecutar(tc.function.name, tc.function.arguments)
            traza.append(
                {"tool": tc.function.name, "argumentos": tc.function.arguments, "resultado": resultado}
            )
            if tc.function.name == "get_team_stats" and resultado.get("ok"):
                ruta = "funcion"
            if tc.function.name == "buscar_documentacion" and resultado.get("ok"):
                if resultado.get("sin_evidencia"):
                    sin_evidencia = True
                else:
                    ruta = "rag" if ruta != "funcion" else ruta
                    fuentes += [f["fuente"] for f in resultado.get("fragmentos", [])]
            # ...y después un mensaje role="tool" por cada tool_call, enlazado por su id.
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(resultado, ensure_ascii=False),
                }
            )

        if sin_evidencia and ruta == "sin_evidencia":
            respuesta = NO_EVIDENCIA  # cortocircuito: ni siquiera dejamos redactar al modelo
            break

    if respuesta is None:
        respuesta = NO_EVIDENCIA  # se agotaron las vueltas
    if ruta == "sin_evidencia" and respuesta != NO_EVIDENCIA:
        # Guardarraíl: sin herramienta no hay respuesta, aunque el modelo "se la sepa".
        traza.append({"guardarrail": "respuesta_sin_herramienta_descartada", "texto": respuesta})
        respuesta = NO_EVIDENCIA

    citadas = _CITA_RE.findall(respuesta)
    return {
        "pregunta": pregunta,
        "ruta": ruta,
        "respuesta": respuesta,
        "fuentes_recuperadas": fuentes,
        "fuentes_citadas": citadas,
        "cita_ok": bool(set(citadas) & set(fuentes)) if ruta == "rag" else None,
        "traza": traza,
        "llamadas_llm": llamadas_llm,
        **tokens,
        "latencia_ms": round((time.perf_counter() - t0) * 1000, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Pregunte sobre los datos de fútbol (tools + RAG)")
    parser.add_argument("pregunta")
    parser.add_argument("--mock", action="store_true", help="Sin API (LLM simulado)")
    parser.add_argument(
        "--embeddings",
        choices=("hash", "real"),
        help="Por defecto: hash con --mock, real sin él",
    )
    args = parser.parse_args()
    usar_hash = (args.embeddings or ("hash" if args.mock else "real")) == "hash"
    r = responder(args.pregunta, mock=args.mock, ejecutor=Ejecutor(mock=usar_hash))
    print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
