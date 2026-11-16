"""Evalúa las 11 preguntas de la semana 2 (función / RAG / sin evidencia)."""

from __future__ import annotations

import argparse
import csv
import re
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Any

from src.rag_tools.agente import NO_EVIDENCIA, responder
from src.rag_tools.tools import Ejecutor
from src.rag_tools.vector_store import Buscador

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV = ROOT / "data" / "preguntas_semana2.csv"
DEFAULT_OUT = ROOT / "results" / "evaluacion_semana2.csv"


def cargar_preguntas(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def es_acierto(tipo: str, esperado: str, r: dict[str, Any]) -> tuple[bool, str]:
    """Devuelve (acierto, motivo). El motivo ayuda a depurar cada fallo."""
    if tipo == "numerica":
        equipo, temporada, condicion, metrica = esperado.split("|")
        campo, valor = metrica.split("=")
        llamadas = [
            t["resultado"]["datos"]
            for t in r["traza"]
            if t.get("tool") == "get_team_stats" and t["resultado"].get("ok")
        ]
        if r["ruta"] != "funcion" or not llamadas:
            return False, f"ruta={r['ruta']} (se esperaba funcion)"
        d = llamadas[-1]
        if (d["team"], d["season"], d["condicion"]) != (equipo, temporada, condicion):
            return False, f"argumentos {d['team']}/{d['season']}/{d['condicion']}"
        if str(d[campo]) != valor:
            return False, f"{campo}={d[campo]} en la función"
        if not re.search(rf"(?<!\d){re.escape(valor)}(?!\d)", r["respuesta"]):
            return False, f"la respuesta no contiene {valor}"
        return True, "ok"
    if tipo == "conceptual":
        if r["ruta"] != "rag":
            return False, f"ruta={r['ruta']} (se esperaba rag)"
        if esperado not in r["fuentes_recuperadas"]:
            return False, "fuente esperada fuera del top-3"
        if not r["cita_ok"]:
            return False, "no cita ninguna fuente recuperada"
        return True, "ok"
    ok = r["ruta"] == "sin_evidencia" and r["respuesta"] == NO_EVIDENCIA
    return ok, "ok" if ok else f"ruta={r['ruta']}"


def run(
    dataset: Path,
    salida: Path,
    *,
    mock: bool,
    embeddings: str,
    pausa: float,
) -> Path:
    usar_hash = embeddings == "hash"
    preguntas = cargar_preguntas(dataset)
    buscador = Buscador(mock=usar_hash)
    ejecutor = Ejecutor(mock=usar_hash, buscador=buscador)

    filas: list[dict[str, Any]] = []
    por_tipo: Counter[str] = Counter()
    aciertos_tipo: Counter[str] = Counter()
    total_tokens = 0
    total_llamadas = 0
    latencias: list[float] = []

    for row in preguntas:
        r = responder(row["pregunta"], mock=mock, ejecutor=ejecutor)
        ok, motivo = es_acierto(row["tipo"], row["esperado"], r)
        tipo = row["tipo"]
        por_tipo[tipo] += 1
        if ok:
            aciertos_tipo[tipo] += 1
        total_tokens += int(r.get("total_tokens") or 0)
        total_llamadas += int(r.get("llamadas_llm") or 0)
        latencias.append(float(r.get("latencia_ms") or 0))

        marca = "OK" if ok else "MAL"
        print(f"[{row['id']:>2}] {marca}  {tipo:<13} ruta={r['ruta']:<14} {motivo}")

        filas.append(
            {
                "id": row["id"],
                "pregunta": row["pregunta"],
                "tipo": tipo,
                "esperado": row["esperado"],
                "ruta": r["ruta"],
                "acierto": ok,
                "motivo": motivo,
                "respuesta": r["respuesta"],
                "fuentes_recuperadas": "|".join(r.get("fuentes_recuperadas") or []),
                "fuentes_citadas": "|".join(r.get("fuentes_citadas") or []),
                "cita_ok": r.get("cita_ok"),
                "llamadas_llm": r.get("llamadas_llm"),
                "prompt_tokens": r.get("prompt_tokens"),
                "completion_tokens": r.get("completion_tokens"),
                "total_tokens": r.get("total_tokens"),
                "latencia_ms": r.get("latencia_ms"),
            }
        )
        if not mock and pausa > 0:
            time.sleep(pausa)

    salida.parent.mkdir(parents=True, exist_ok=True)
    with salida.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(filas[0].keys()))
        writer.writeheader()
        writer.writerows(filas)

    for tipo in ("numerica", "conceptual", "fuera_corpus"):
        if por_tipo[tipo]:
            print(f"{tipo:<13} aciertos={aciertos_tipo[tipo]}/{por_tipo[tipo]}")
    mediana = statistics.median(latencias) if latencias else 0
    total_ok = sum(aciertos_tipo.values())
    print(
        f"TOTAL aciertos={total_ok}/{len(filas)} | llamadas_llm={total_llamadas} | "
        f"tokens={total_tokens} | latencia mediana={mediana:.0f} ms"
    )
    print(f"Escrito: {salida}")
    return salida


def main() -> None:
    parser = argparse.ArgumentParser(description="Evalúa function calling + RAG (semana 2)")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--mock", action="store_true", help="LLM simulado")
    parser.add_argument(
        "--embeddings",
        choices=("hash", "real"),
        default=None,
        help="Por defecto: hash con --mock, real sin él",
    )
    parser.add_argument(
        "--pausa",
        type=float,
        default=4.0,
        help="Pausa entre preguntas con API real (rate limit)",
    )
    args = parser.parse_args()
    embeddings = args.embeddings or ("hash" if args.mock else "real")
    run(
        args.dataset,
        args.out,
        mock=args.mock,
        embeddings=embeddings,
        pausa=args.pausa,
    )


if __name__ == "__main__":
    main()
