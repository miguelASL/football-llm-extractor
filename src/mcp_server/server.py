"""Servidor MCP local (stdio) con las herramientas de la semana 2.

Regla de oro con stdio: stdout es el canal del protocolo (JSON-RPC).
Nada de print(): los logs van a stderr con logging.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import sys
from typing import Annotated, Literal

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field, ValidationError

from src.rag_tools.chunking import DICCIONARIO_MD
from src.rag_tools.stats import PARTIDOS_CSV, TeamStats, TeamStatsArgs
from src.rag_tools.stats import get_team_stats as calcular_stats
from src.rag_tools.vector_store import Buscador, umbral_por_defecto

# ---------------------------------------------------------------------------
# Logging (stderr — nunca stdout)
# ---------------------------------------------------------------------------

logging.basicConfig(
    stream=sys.stderr,
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("futbol_mcp")

# Modo mock: embeddings de juguete, sin descargas (útil para tests e Inspector).
MOCK = os.getenv("FUTBOL_MCP_MOCK", "0") == "1"

# ---------------------------------------------------------------------------
# Servidor MCP
# ---------------------------------------------------------------------------

mcp = MCPServer(
    "futbol-datos",
    instructions=(
        "Datos FICTICIOS de partidos de 6 equipos (temporadas 2022/23 y 2023/24). "
        "Use get_team_stats para cualquier cifra y buscar_documentacion para definiciones."
    ),
)

SOLO_LECTURA = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
)

# ---------------------------------------------------------------------------
# Modelos de salida (búsqueda documental)
# ---------------------------------------------------------------------------

DESCRIPCION_COLUMNAS = {
    "partido_id": "Identificador único del partido (p. ej. 2023-07)",
    "temporada": "Temporada en formato YYYY/YY",
    "fecha": "Fecha ISO (YYYY-MM-DD)",
    "equipo_local": "Nombre canónico del equipo que juega en casa",
    "equipo_visitante": "Nombre canónico del equipo que juega fuera",
    "goles_local": "Goles del equipo local (entero >= 0)",
    "goles_visitante": "Goles del equipo visitante (entero >= 0)",
}


class FragmentoOut(BaseModel):
    fuente: str
    distancia: float
    texto: str


class ResultadoBusqueda(BaseModel):
    sin_evidencia: bool
    mejor_distancia: float | None
    umbral: float
    fragmentos: list[FragmentoOut]


# ---------------------------------------------------------------------------
# Buscador (carga perezosa)
# ---------------------------------------------------------------------------

_buscador: Buscador | None = None


def _get_buscador() -> Buscador:
    global _buscador
    if _buscador is None:  # perezoso: cargar e5-small tarda unos segundos
        log.info("Cargando buscador (mock=%s)", MOCK)
        _buscador = Buscador(mock=MOCK)
    return _buscador


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool(annotations=SOLO_LECTURA)
def get_team_stats(
    team: Annotated[str, Field(description="Equipo, p. ej. 'Real Betis' o 'Barça'")],
    season: Annotated[str, Field(description="Temporada en formato YYYY/YY, p. ej. '2023/24'")],
    condicion: Annotated[
        Literal["local", "visitante", "global"],
        Field(description="local = en casa, visitante = fuera, global = todos"),
    ] = "global",
) -> TeamStats:
    """Cifras exactas (partidos, victorias, empates, derrotas, goles, porterías a cero y puntos)
    de un equipo en una temporada. Úsela para CUALQUIER pregunta que pida un número."""
    log.info("get_team_stats team=%r season=%r condicion=%r", team, season, condicion)
    try:
        args = TeamStatsArgs(team=team, season=season, condicion=condicion)
    except ValidationError as exc:
        # Error previsto -> ToolError -> isError=true con un mensaje que el modelo entiende.
        detalle = "; ".join(
            f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()
        )
        raise ToolError(f"Argumentos inválidos: {detalle}") from exc
    try:
        return calcular_stats(args.team, args.season, args.condicion)
    except LookupError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool(annotations=SOLO_LECTURA)
def buscar_documentacion(
    consulta: Annotated[
        str, Field(min_length=3, description="La pregunta o los términos a buscar")
    ],
) -> ResultadoBusqueda:
    """Busca en el diccionario de datos definiciones, reglas de cálculo y limitaciones.
    Para preguntas conceptuales. No devuelve cifras de partidos."""
    umbral = umbral_por_defecto(MOCK)
    resultados = _get_buscador().buscar(consulta, k=3)
    mejor = resultados[0].distancia if resultados else None
    log.info("buscar_documentacion %r -> mejor=%s umbral=%s", consulta, mejor, umbral)
    if mejor is None or mejor > umbral:
        return ResultadoBusqueda(
            sin_evidencia=True,
            mejor_distancia=mejor,
            umbral=umbral,
            fragmentos=[],
        )
    return ResultadoBusqueda(
        sin_evidencia=False,
        mejor_distancia=mejor,
        umbral=umbral,
        fragmentos=[
            FragmentoOut(fuente=r.id, distancia=r.distancia, texto=r.texto)
            for r in resultados
        ],
    )


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

@mcp.resource(
    "futbol://esquema/partidos",
    name="esquema_partidos",
    description="Columnas, tipos y cobertura de data/partidos_ejemplo.csv",
    mime_type="application/json",
)
def esquema_partidos() -> str:
    with PARTIDOS_CSV.open(encoding="utf-8", newline="") as fh:
        filas = list(csv.DictReader(fh))
    esquema = {
        "fichero": "data/partidos_ejemplo.csv",
        "aviso": "Datos FICTICIOS generados con semilla fija",
        "filas": len(filas),
        "temporadas": sorted({f["temporada"] for f in filas}),
        "equipos": sorted({f["equipo_local"] for f in filas}),
        "columnas": [
            {
                "nombre": c,
                "tipo": "int" if c.startswith("goles") else "str",
                "descripcion": d,
            }
            for c, d in DESCRIPCION_COLUMNAS.items()
        ],
    }
    return json.dumps(esquema, ensure_ascii=False, indent=2)


@mcp.resource(
    "futbol://docs/diccionario",
    name="diccionario_datos",
    description="Diccionario de datos y reglas de métricas (markdown completo)",
    mime_type="text/markdown",
)
def diccionario() -> str:
    return DICCIONARIO_MD.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

@mcp.prompt(title="Informe de un equipo")
def informe_equipo(team: str, season: str) -> str:
    """Plantilla que elige el usuario: pide un informe breve con cifras de las tools."""
    return (
        f"Haz un informe breve del {team} en la temporada {season}. "
        "Obtén las cifras con get_team_stats (global, local y visitante) y explica "
        "cada métrica con buscar_documentacion, citando la fuente. "
        "Indica que los datos son ficticios."
    )


# ---------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("Arrancando servidor MCP futbol-datos por stdio (mock=%s)", MOCK)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
