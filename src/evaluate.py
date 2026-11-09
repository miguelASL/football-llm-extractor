"""Evalúa el dataset de preguntas con prompt vago y claro."""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path
from typing import Any

from src.extractor import extraer

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = ROOT / "data" / "preguntas.csv"
DEFAULT_OUT = ROOT / "results" / "evaluacion.csv"


def cargar_preguntas(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def fila_resultado(pregunta_id: str, notas: str, tipo: str, r: dict[str, Any]) -> dict[str, Any]:
    # El LLM (sobre todo prompt vago) a veces devuelve una lista JSON, no un objeto.
    raw_datos = r.get("datos")
    datos = raw_datos if isinstance(raw_datos, dict) else {}
    return {
        "id": pregunta_id,
        "notas": notas,
        "tipo_prompt": tipo,
        "pregunta": r.get("pregunta"),
        "parse_ok": r.get("parse_ok"),
        "validacion_ok": r.get("validacion_ok"),
        "es_valida": datos.get("es_valida"),
        "error": datos.get("error"),
        "equipo": datos.get("equipo"),
        "temporada": datos.get("temporada"),
        "metrica": datos.get("metrica"),
        "condicion": datos.get("condicion"),
        "prompt_tokens": r.get("prompt_tokens"),
        "completion_tokens": r.get("completion_tokens"),
        "total_tokens": r.get("total_tokens"),
        "latencia_ms": r.get("latencia_ms"),
        "error_parseo": r.get("error_parseo"),
        "error_validacion": r.get("error_validacion"),
    }


def resumen(filas: list[dict[str, Any]]) -> None:
    for tipo in ("vago", "claro"):
        subset = [f for f in filas if f["tipo_prompt"] == tipo]
        if not subset:
            continue
        validos = sum(1 for f in subset if f.get("es_valida") is True)
        parse_ok = sum(1 for f in subset if f.get("parse_ok") in (True, "True", "true"))
        tokens = sum(int(f["total_tokens"] or 0) for f in subset)
        print(
            f"[{tipo}] válidos={validos}/{len(subset)} "
            f"parse_ok={parse_ok}/{len(subset)} total_tokens={tokens}"
        )


def run(dataset: Path, salida: Path, mock: bool, pause_s: float) -> Path:
    preguntas = cargar_preguntas(dataset)
    filas: list[dict[str, Any]] = []

    for row in preguntas:
        for tipo in ("vago", "claro"):
            resultado = extraer(row["pregunta"], tipo_prompt=tipo, mock=mock)
            filas.append(fila_resultado(row["id"], row.get("notas", ""), tipo, resultado))
            if not mock and pause_s > 0:
                time.sleep(pause_s)

    salida.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(filas[0].keys()) if filas else []
    with salida.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filas)

    print(f"Escrito: {salida}")
    resumen(filas)
    return salida


def main() -> None:
    parser = argparse.ArgumentParser(description="Evalúa prompts vago vs claro")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--mock", action="store_true", help="Sin API, tubería offline")
    parser.add_argument(
        "--pause",
        type=float,
        default=0.5,
        help="Pausa entre llamadas reales (rate limit)",
    )
    args = parser.parse_args()
    run(args.dataset, args.out, mock=args.mock, pause_s=args.pause)


if __name__ == "__main__":
    main()
