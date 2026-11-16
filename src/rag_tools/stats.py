"""La herramienta numérica: get_team_stats(team, season, condicion).

Regla de oro: las cifras salen de aquí (código determinista sobre el CSV),
nunca de una búsqueda por similitud ni de la memoria del modelo.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, field_validator

ROOT = Path(__file__).resolve().parents[2]
PARTIDOS_CSV = ROOT / "data" / "partidos_ejemplo.csv"

# Alias en minúsculas y sin tildes -> nombre canónico del CSV.
ALIAS_EQUIPOS: dict[str, str] = {
    "real betis": "Real Betis",
    "betis": "Real Betis",
    "sevilla": "Sevilla FC",
    "sevilla fc": "Sevilla FC",
    "malaga": "Málaga CF",
    "malaga cf": "Málaga CF",
    "real madrid": "Real Madrid",
    "madrid": "Real Madrid",
    "barcelona": "FC Barcelona",
    "fc barcelona": "FC Barcelona",
    "barca": "FC Barcelona",
    "athletic": "Athletic Club",
    "athletic club": "Athletic Club",
    "athletic de bilbao": "Athletic Club",
}


def _sin_tildes(texto: str) -> str:
    normal = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in normal if not unicodedata.combining(c)).lower().strip()


class TeamStatsArgs(BaseModel):
    """Contrato de los argumentos que propone el modelo. Se valida ANTES de ejecutar."""

    team: str
    season: str
    condicion: Literal["local", "visitante", "global"] = "global"

    @field_validator("team")
    @classmethod
    def normalizar_equipo(cls, value: str) -> str:
        clave = _sin_tildes(value)
        if clave not in ALIAS_EQUIPOS:
            conocidos = sorted(set(ALIAS_EQUIPOS.values()))
            raise ValueError(f"Equipo desconocido: {value!r}. Equipos válidos: {conocidos}")
        return ALIAS_EQUIPOS[clave]

    @field_validator("season")
    @classmethod
    def normalizar_temporada(cls, value: str) -> str:
        texto = value.strip().replace(" ", "")
        m = re.fullmatch(r"(\d{4})[/-](\d{2}|\d{4})", texto)
        if not m:
            raise ValueError("La temporada debe tener formato YYYY/YY, p. ej. 2023/24")
        inicio, fin = int(m.group(1)), int(m.group(2)[-2:])
        if (inicio + 1) % 100 != fin:
            raise ValueError(f"Temporada incoherente: {value!r}")
        return f"{inicio}/{fin:02d}"


class TeamStats(BaseModel):
    team: str
    season: str
    condicion: str
    partidos: int
    victorias: int
    empates: int
    derrotas: int
    goles_favor: int
    goles_contra: int
    diferencia_goles: int
    porterias_a_cero: int
    puntos: int
    fuente: str = "data/partidos_ejemplo.csv (datos FICTICIOS)"


@lru_cache(maxsize=1)
def cargar_partidos(path: Path = PARTIDOS_CSV) -> tuple[dict[str, str], ...]:
    with path.open(encoding="utf-8", newline="") as fh:
        return tuple(csv.DictReader(fh))


def get_team_stats(team: str, season: str, condicion: str = "global") -> TeamStats:
    """Calcula las estadísticas de un equipo en una temporada (argumentos ya validados)."""
    partidos = [p for p in cargar_partidos() if p["temporada"] == season]
    if not partidos:
        raise LookupError(f"No hay datos de la temporada {season}")

    v = e = d = gf = gc = cero = n = 0
    for p in partidos:
        if p["equipo_local"] == team and condicion in ("local", "global"):
            propios, ajenos = int(p["goles_local"]), int(p["goles_visitante"])
        elif p["equipo_visitante"] == team and condicion in ("visitante", "global"):
            propios, ajenos = int(p["goles_visitante"]), int(p["goles_local"])
        else:
            continue
        n += 1
        gf += propios
        gc += ajenos
        cero += ajenos == 0
        if propios > ajenos:
            v += 1
        elif propios == ajenos:
            e += 1
        else:
            d += 1

    return TeamStats(
        team=team,
        season=season,
        condicion=condicion,
        partidos=n,
        victorias=v,
        empates=e,
        derrotas=d,
        goles_favor=gf,
        goles_contra=gc,
        diferencia_goles=gf - gc,
        porterias_a_cero=cero,
        puntos=3 * v + e,
    )
