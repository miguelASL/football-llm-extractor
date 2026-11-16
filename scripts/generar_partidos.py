"""Genera data/partidos_ejemplo.csv con resultados FICTICIOS (semilla fija).

Los equipos son reales, pero los marcadores son inventados para practicar.
Con la misma semilla, cualquier ordenador genera exactamente el mismo CSV.
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from itertools import permutations
from pathlib import Path

EQUIPOS = ["Real Betis", "Sevilla FC", "Málaga CF", "Real Madrid", "FC Barcelona", "Athletic Club"]
TEMPORADAS = {"2022/23": date(2022, 8, 14), "2023/24": date(2023, 8, 13)}
SEMILLA = 42
SALIDA = Path(__file__).resolve().parent.parent / "data" / "partidos_ejemplo.csv"


def generar() -> list[dict[str, object]]:
    rng = random.Random(SEMILLA)
    filas: list[dict[str, object]] = []
    for temporada, inicio in TEMPORADAS.items():
        # Liga a doble vuelta: cada pareja juega una vez en cada campo (30 partidos).
        cruces = list(permutations(EQUIPOS, 2))
        rng.shuffle(cruces)
        for i, (local, visitante) in enumerate(cruces):
            filas.append(
                {
                    "partido_id": f"{temporada[:4]}-{i + 1:02d}",
                    "temporada": temporada,
                    "fecha": (inicio + timedelta(days=4 * i)).isoformat(),
                    "equipo_local": local,
                    "equipo_visitante": visitante,
                    "goles_local": rng.randint(0, 4),
                    "goles_visitante": rng.randint(0, 3),
                }
            )
    return filas


def main() -> None:
    filas = generar()
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    with SALIDA.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(filas[0].keys()))
        writer.writeheader()
        writer.writerows(filas)
    print(f"Escrito {SALIDA} con {len(filas)} partidos ficticios")


if __name__ == "__main__":
    main()
