"""Estrategias de prompt: vago (zero-shot) vs claro (few-shot)."""

from __future__ import annotations

from typing import Any

FEW_SHOT_EJEMPLOS: list[dict[str, str]] = [
    {
        "role": "user",
        "content": "¿Cuántos goles marcó el Betis en casa en la 2023/24?",
    },
    {
        "role": "assistant",
        "content": (
            '{"equipo":"Real Betis","temporada":"2023/24","metrica":"goles",'
            '"condicion":"local","es_valida":true,"error":null}'
        ),
    },
    {
        "role": "user",
        "content": "¿Cuántos goles marcó el Málaga en casa?",
    },
    {
        "role": "assistant",
        "content": (
            '{"equipo":"Málaga","temporada":null,"metrica":"goles",'
            '"condicion":"local","es_valida":false,"error":"falta_temporada"}'
        ),
    },
]

SYSTEM_CLARO = """Eres un extractor de intenciones sobre estadísticas de fútbol.
Devuelve SOLO un objeto JSON con exactamente estas claves:
equipo, temporada, metrica, condicion, es_valida, error.

Reglas:
1. No inventes datos que no estén en la pregunta.
2. condicion debe ser solo: local | visitante | global (o null).
3. temporada en formato YYYY/YY si aparece (normaliza 2023-2024 → 2023/24).
4. Si falta temporada → es_valida=false, error="falta_temporada".
5. Si el equipo es ambiguo (p.ej. "equipo de Pacheta") → es_valida=false, error="equipo_ambiguo".
6. Si la pregunta no es de fútbol → es_valida=false, error="no_futbolistica".
7. Si pregunta por un jugador y no un equipo de club → es_valida=false, error="jugador_no_equipo".
8. Si la pregunta compara dos equipos sin un único sujeto claro → puedes poner es_valida=false
   y error="comparacion_dos_equipos", o extraer el primero y marcar error si hace falta.
9. Campos desconocidos → null. Nunca inventes temporada ni equipo.
10. es_valida=true solo si equipo, temporada y metrica están presentes y claros.
"""


def mensajes_prompt_vago(pregunta: str) -> list[dict[str, Any]]:
    return [
        {
            "role": "system",
            "content": "Extrae datos de fútbol de la pregunta y dame JSON.",
        },
        {"role": "user", "content": pregunta},
    ]


def mensajes_prompt_claro(pregunta: str) -> list[dict[str, Any]]:
    return [
        {"role": "system", "content": SYSTEM_CLARO},
        *FEW_SHOT_EJEMPLOS,
        {"role": "user", "content": pregunta},
    ]


def construir_mensajes(pregunta: str, tipo_prompt: str) -> list[dict[str, Any]]:
    tipo = tipo_prompt.strip().lower()
    if tipo == "vago":
        return mensajes_prompt_vago(pregunta)
    if tipo == "claro":
        return mensajes_prompt_claro(pregunta)
    raise ValueError(f"tipo_prompt desconocido: {tipo_prompt!r}. Use 'vago' o 'claro'.")
