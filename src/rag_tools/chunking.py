"""Trocea el diccionario de datos en fragmentos: una sección '## ' = un fragmento."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DICCIONARIO_MD = ROOT / "docs" / "diccionario_datos.md"


@dataclass(frozen=True)
class Fragmento:
    id: str  # p. ej. "diccionario_datos.md#puntos": es la cita que verá el usuario
    titulo: str
    texto: str


def slug(titulo: str) -> str:
    normal = unicodedata.normalize("NFKD", titulo)
    ascii_ = "".join(c for c in normal if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_).strip("-")


def trocear_markdown(path: Path = DICCIONARIO_MD) -> list[Fragmento]:
    fragmentos: list[Fragmento] = []
    titulo: str | None = None
    lineas: list[str] = []

    def cerrar() -> None:
        if titulo and "".join(lineas).strip():
            cuerpo = " ".join(l.strip() for l in lineas if l.strip())
            # El título va dentro del texto: ayuda mucho a la búsqueda.
            fragmentos.append(
                Fragmento(id=f"{path.name}#{slug(titulo)}", titulo=titulo, texto=f"{titulo}. {cuerpo}")
            )

    for linea in path.read_text(encoding="utf-8").splitlines():
        if linea.startswith("## "):
            cerrar()
            titulo, lineas = linea[3:].strip(), []
        elif titulo is not None:
            lineas.append(linea)
    cerrar()
    return fragmentos
