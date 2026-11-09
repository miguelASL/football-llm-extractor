"""Contrato de datos para la extracción futbolística."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Condicion(str, Enum):
    LOCAL = "local"
    VISITANTE = "visitante"
    GLOBAL = "global"


class ExtraccionFutbol(BaseModel):
    equipo: Optional[str] = None
    temporada: Optional[str] = None  # idealmente YYYY/YY
    metrica: Optional[str] = None
    condicion: Optional[Condicion] = None
    es_valida: bool
    error: Optional[str] = Field(
        default=None,
        description="Código de error semántico, p.ej. falta_temporada",
    )

    @field_validator("temporada")
    @classmethod
    def normalizar_temporada(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        texto = value.strip().replace(" ", "")
        if "-" in texto and "/" not in texto:
            a, b = texto.split("-", 1)
            if len(a) == 4 and len(b) == 4:
                return f"{a}/{b[-2:]}"  # 2023-2024 → 2023/24
        return texto
