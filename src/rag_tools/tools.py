"""Esquemas de las herramientas (lo que ve el modelo) y su ejecución segura (lo que hace su código)."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from src.rag_tools.stats import TeamStatsArgs, get_team_stats
from src.rag_tools.vector_store import Buscador, umbral_por_defecto

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_team_stats",
            "description": (
                "Devuelve cifras exactas (partidos, victorias, empates, derrotas, goles a favor, "
                "goles en contra, diferencia de goles, porterías a cero y puntos) de un equipo en "
                "una temporada. Úsela para CUALQUIER pregunta que pida un número."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "team": {"type": "string", "description": "Equipo, p. ej. 'Real Betis' o 'Barça'"},
                    "season": {
                        "type": "string",
                        "description": "Temporada en formato YYYY/YY, p. ej. '2023/24'",
                    },
                    "condicion": {
                        "type": "string",
                        "enum": ["local", "visitante", "global"],
                        "description": "local = en casa, visitante = fuera, global = todos (por defecto)",
                    },
                },
                "required": ["team", "season"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_documentacion",
            "description": (
                "Busca en el diccionario de datos del proyecto definiciones, reglas de cálculo de "
                "métricas y limitaciones. Úsela para preguntas conceptuales (qué significa, cómo se "
                "calcula). No devuelve cifras de partidos."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "consulta": {
                        "type": "string",
                        "description": "La pregunta o los términos a buscar",
                    }
                },
                "required": ["consulta"],
            },
        },
    },
]


class BuscarArgs(BaseModel):
    consulta: str = Field(min_length=3)


class Ejecutor:
    """Valida los argumentos con Pydantic y, solo si son correctos, ejecuta la función."""

    def __init__(self, mock: bool = False, buscador: Buscador | None = None) -> None:
        self.mock = mock
        self._buscador = buscador
        self.umbral = umbral_por_defecto(mock)

    @property
    def buscador(self) -> Buscador:
        if self._buscador is None:  # se crea al primer uso: cargar embeddings tarda
            self._buscador = Buscador(mock=self.mock)
        return self._buscador

    def ejecutar(self, nombre: str, argumentos_json: str) -> dict[str, Any]:
        try:
            crudos = json.loads(argumentos_json or "{}")
        except json.JSONDecodeError as exc:
            return {"ok": False, "error": "argumentos_no_json", "detalle": str(exc)}

        try:
            if nombre == "get_team_stats":
                args = TeamStatsArgs.model_validate(crudos)
                stats = get_team_stats(args.team, args.season, args.condicion)
                return {"ok": True, "datos": stats.model_dump()}
            if nombre == "buscar_documentacion":
                args_b = BuscarArgs.model_validate(crudos)
                resultados = self.buscador.buscar(args_b.consulta, k=3)
                if not resultados or resultados[0].distancia > self.umbral:
                    mejor = resultados[0].distancia if resultados else None
                    return {
                        "ok": True,
                        "sin_evidencia": True,
                        "mejor_distancia": mejor,
                        "umbral": self.umbral,
                    }
                return {
                    "ok": True,
                    "sin_evidencia": False,
                    "fragmentos": [
                        {"fuente": r.id, "distancia": r.distancia, "texto": r.texto}
                        for r in resultados
                    ],
                }
        except ValidationError as exc:
            # No se ejecuta nada: se devuelve el error al modelo para que corrija.
            errores = [
                {"campo": ".".join(map(str, e["loc"])), "mensaje": e["msg"]} for e in exc.errors()
            ]
            return {"ok": False, "error": "argumentos_invalidos", "detalle": errores}
        except LookupError as exc:
            return {"ok": False, "error": "sin_datos", "detalle": str(exc)}
        return {"ok": False, "error": "herramienta_desconocida", "detalle": nombre}
