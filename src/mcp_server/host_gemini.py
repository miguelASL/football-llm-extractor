"""Host mínimo (OPCIONAL): conecta Gemini con el servidor MCP.

host_gemini.py = host + cliente MCP. Lanza el servidor por stdio, descubre sus
tools con list_tools, se las traduce al formato del proveedor (OpenAI/Gemini)
y ejecuta con call_tool lo que pida el modelo. El modelo nunca habla con MCP.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from mcp import Client, StdioServerParameters
from mcp.types import CallToolResult, Tool
from openai.types.chat.chat_completion_message_function_tool_call import (
    ChatCompletionMessageFunctionToolCall,
)

from src.rag_tools.agente import MAX_VUELTAS, NO_EVIDENCIA, SYSTEM
from src.rag_tools.llm import llamar_con_tools

ROOT = Path(__file__).resolve().parents[2]


def mcp_a_openai(tool: Tool) -> dict[str, Any]:
    """Traduce una tool MCP al formato 'tools' del SDK de OpenAI (que Gemini acepta)."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.input_schema,  # MCP ya trae JSON Schema: no se reescribe a mano
        },
    }


def resultado_a_dict(nombre: str, r: CallToolResult) -> dict[str, Any]:
    """Mismo sobre que el Ejecutor de la semana 2, para reutilizar SYSTEM y el mock."""
    if r.is_error:
        texto = " ".join(c.text for c in r.content if c.type == "text")
        return {"ok": False, "error": "tool_error", "detalle": texto}
    datos = r.structured_content or {}
    if nombre == "get_team_stats":
        return {"ok": True, "datos": datos}
    return {"ok": True, **datos}


async def responder(pregunta: str, *, mock: bool = False, embeddings_mock: bool | None = None) -> dict[str, Any]:
    usar_hash = mock if embeddings_mock is None else embeddings_mock
    params = StdioServerParameters(
        command=sys.executable,  # el mismo Python del venv: evita "No module named mcp"
        args=["-m", "src.mcp_server.server"],
        cwd=str(ROOT),  # ruta absoluta: el host puede arrancar desde cualquier carpeta
        env={**os.environ, "FUTBOL_MCP_MOCK": "1" if usar_hash else "0"},
    )
    traza: list[dict[str, Any]] = []
    async with Client(params, read_timeout_seconds=120) as cliente:
        tools = [mcp_a_openai(t) for t in (await cliente.list_tools()).tools]
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": pregunta},
        ]
        for _ in range(MAX_VUELTAS):
            # La llamada al modelo es síncrona: se manda a un hilo para no bloquear el bucle asyncio.
            completion = await asyncio.to_thread(llamar_con_tools, messages, tools, mock=mock)
            msg = completion.choices[0].message
            if not msg.tool_calls:
                return {"respuesta": (msg.content or "").strip() or NO_EVIDENCIA, "traza": traza}
            # model_dump conserva extra_content (thought_signature de Gemini) si viene.
            messages.append(msg.model_dump(exclude_none=True))
            for tc in msg.tool_calls:
                # tool_calls es Union[function, custom]; solo manejamos function tools.
                if not isinstance(tc, ChatCompletionMessageFunctionToolCall):
                    continue
                args = json.loads(tc.function.arguments or "{}")
                r = await cliente.call_tool(tc.function.name, args)  # aquí es donde entra MCP
                resultado = resultado_a_dict(tc.function.name, r)
                traza.append({"tool": tc.function.name, "argumentos": args, "is_error": r.is_error})
                if resultado.get("sin_evidencia"):
                    return {"respuesta": NO_EVIDENCIA, "traza": traza}
                messages.append({"role": "tool", "tool_call_id": tc.id,
                                 "content": json.dumps(resultado, ensure_ascii=False)})
    return {"respuesta": NO_EVIDENCIA, "traza": traza}


def main() -> None:
    parser = argparse.ArgumentParser(description="Gemini + servidor MCP de fútbol (host mínimo)")
    parser.add_argument("pregunta")
    parser.add_argument("--mock", action="store_true", help="LLM y embeddings simulados (sin clave)")
    args = parser.parse_args()
    r = asyncio.run(responder(args.pregunta, mock=args.mock))
    print(json.dumps(r, ensure_ascii=False, indent=2))  # aquí print SÍ vale: esto es el host, no el servidor


if __name__ == "__main__":
    main()