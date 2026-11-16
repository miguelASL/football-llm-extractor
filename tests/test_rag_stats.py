"""Tests de get_team_stats y el contrato TeamStatsArgs."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.rag_tools.stats import TeamStatsArgs, get_team_stats


def test_normaliza_alias_y_temporada():
    a = TeamStatsArgs(team="Betis", season="2023-2024")
    assert a.team == "Real Betis"
    assert a.season == "2023/24"
    assert a.condicion == "global"


def test_barca_y_condicion_local():
    a = TeamStatsArgs(team="Barça", season="2023/24", condicion="local")
    assert a.team == "FC Barcelona"
    assert a.condicion == "local"


def test_equipo_desconocido_invalido():
    with pytest.raises(ValidationError):
        TeamStatsArgs(team="Atlético", season="2023/24")


def test_temporada_incoherente():
    with pytest.raises(ValidationError):
        TeamStatsArgs(team="Betis", season="2023/25")


def test_puntos_betis_2023_24():
    a = TeamStatsArgs(team="Betis", season="2023-2024")
    stats = get_team_stats(**a.model_dump())
    assert stats.puntos == 19
    assert stats.partidos == 10
    assert "FICTICIOS" in stats.fuente


def test_local_mas_visitante_igual_global():
    team, season = "Sevilla FC", "2022/23"
    local = get_team_stats(team, season, "local")
    visitante = get_team_stats(team, season, "visitante")
    global_ = get_team_stats(team, season, "global")
    assert local.partidos + visitante.partidos == global_.partidos
    assert local.goles_favor + visitante.goles_favor == global_.goles_favor
    assert local.puntos + visitante.puntos == global_.puntos
