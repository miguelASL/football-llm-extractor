"""Carga y valida configuración desde variables de entorno."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

_PLACEHOLDERS = {
    "",
    "pegue_aqui_su_clave_de_google_ai_studio",
    "sk-...",
}


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    api_key: str
    base_url: str
    model: str
    timeout_seconds: float
    max_retries: int


def _normalize_base_url(url: str) -> str:
    """El SDK concatena rutas; la barra final importa."""
    return url if url.endswith("/") else f"{url}/"


def get_settings() -> Settings:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key or api_key in _PLACEHOLDERS:
        raise ValueError(
            "Falta OPENAI_API_KEY. Copie .env.example a .env y pegue una clave real."
        )

    base_url = os.getenv(
        "OPENAI_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    ).strip()

    return Settings(
        llm_provider=(os.getenv("LLM_PROVIDER") or "gemini").strip().lower(),
        api_key=api_key,
        base_url=_normalize_base_url(base_url),
        model=(os.getenv("OPENAI_MODEL") or "gemini-3.5-flash-lite").strip(),
        timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "30")),
        max_retries=int(os.getenv("MAX_RETRIES", "3")),
    )
