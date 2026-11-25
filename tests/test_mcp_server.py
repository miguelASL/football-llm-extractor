"""Tests del servidor MCP: en proceso (rápidos) y por stdio (como lo usará un host real)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters
from mcp.types import TextResourceContents

os.environ["FUTBOL_MCP_MOCK"] = "1"  # embeddings de juguete: sin descargas ni claves

from src.mcp_server.server import mcp  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_lista_las_dos_tools_con_esquema_tipado():
    async with Client(mcp) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
    assert set(tools) == {"get_team_stats", "buscar_documentacion"}
    esquema = tools["get_team_stats"].input_schema
    assert esquema["required"] == ["team", "season"]
    assert esquema["properties"]["condicion"]["enum"] == ["local", "visitante", "global"]
    assert tools["get_team_stats"].annotations.read_only_hint is True  # type: ignore


async def test_llamada_valida_devuelve_datos_estructurados():
    async with Client(mcp) as client:
        r = await client.call_tool("get_team_stats", {"team": "Betis", "season": "2023-2024"})
    assert r.is_error is False
    assert r.structured_content["team"] == "Real Betis"
    assert r.structured_content["puntos"] == 19


@pytest.mark.parametrize(
    "args,fragmento",
    [
        ({"team": "Atlético", "season": "2023/24"}, "Equipo desconocido"),  # lo rechaza TeamStatsArgs
        ({"team": "Betis", "season": "2023/24", "condicion": "en casa"}, "condicion"),  # lo rechaza el SDK
        ({"team": "Betis", "season": "2019/20"}, "No hay datos"),  # LookupError -> ToolError
    ],
)
async def test_entrada_invalida_es_error_controlado(args, fragmento):
    async with Client(mcp) as client:
        r = await client.call_tool("get_team_stats", args)
    assert r.is_error is True  # error de la tool, no del protocolo: el modelo lo puede leer
    assert fragmento in r.content[0].text


async def test_resource_esquema_csv():
    async with Client(mcp) as client:
        uris = [str(r.uri) for r in (await client.list_resources()).resources]
        contenido = await client.read_resource("futbol://esquema/partidos")
    assert "futbol://esquema/partidos" in uris
    bloque = contenido.contents[0]
    assert isinstance(bloque, TextResourceContents)
    assert '"filas": 60' in bloque.text


async def test_stdio_de_verdad_stdout_limpio():
    """Lanza el servidor como subproceso, igual que haría un host."""
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.mcp_server.server"],
        cwd=str(ROOT),
        env={**os.environ, "FUTBOL_MCP_MOCK": "1"},
    )
    async with Client(params, read_timeout_seconds=60) as client:
        tools = [t.name for t in (await client.list_tools()).tools]
        r = await client.call_tool("get_team_stats", {"team": "Sevilla", "season": "2022/23", "condicion": "local"})
    assert "get_team_stats" in tools
    assert r.structured_content["goles_favor"] == 12


def test_stdout_solo_lleva_json_rpc():
    """Habla el protocolo a mano: TODA línea que salga por stdout debe ser JSON-RPC.

    Si alguien añade un print(), aparece una línea que no es JSON y el test falla.
    """
    import json
    import subprocess

    peticion = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "0"},
        },
    }
    # Enviamos una petición y cerramos stdin: el servidor responde y termina.
    proc = subprocess.run(
        [sys.executable, "-m", "src.mcp_server.server"],
        cwd=ROOT,
        env={**os.environ, "FUTBOL_MCP_MOCK": "1"},
        input=json.dumps(peticion) + "\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    lineas = [l for l in proc.stdout.splitlines() if l.strip()]
    mensajes = [json.loads(l) for l in lineas]  # falla si alguna línea no es JSON
    assert all(m["jsonrpc"] == "2.0" for m in mensajes)
    assert mensajes[0]["result"]["serverInfo"]["name"] == "futbol-datos"
    assert "Arrancando servidor" in proc.stderr  # los logs sí existen, pero en stderr