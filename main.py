"""CLI: extrae intención futbolística de una pregunta en lenguaje natural."""

from __future__ import annotations

import argparse
import json
import sys

from src.extractor import extraer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Extractor de preguntas de fútbol → JSON validado (Pydantic)"
    )
    parser.add_argument("pregunta", help="Pregunta en lenguaje natural")
    parser.add_argument(
        "--prompt",
        choices=("vago", "claro"),
        default="claro",
        help="Estrategia de prompt",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="No llama a la API; usa respuesta simulada",
    )
    args = parser.parse_args(argv)

    resultado = extraer(args.pregunta, tipo_prompt=args.prompt, mock=args.mock)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
