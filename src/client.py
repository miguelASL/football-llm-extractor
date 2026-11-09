"""Cliente OpenAI-compatible con timeout y reintentos (tenacity)."""

from __future__ import annotations

from typing import Any

from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import Settings, get_settings


def crear_cliente(settings: Settings | None = None) -> OpenAI:
    cfg = settings or get_settings()
    return OpenAI(
        api_key=cfg.api_key,
        base_url=cfg.base_url,
        timeout=cfg.timeout_seconds,
    )


def llamar_chat(
    messages: list[dict[str, Any]],
    *,
    settings: Settings | None = None,
    client: OpenAI | None = None,
) -> Any:
    """Llamada chat.completions con response_format json_object y reintentos."""
    cfg = settings or get_settings()
    cli = client or crear_cliente(cfg)

    @retry(
        stop=stop_after_attempt(cfg.max_retries),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(
            (RateLimitError, APITimeoutError, APIConnectionError)
        ),
        reraise=True,
    )
    def _llamar() -> Any:
        return cli.chat.completions.create(
            model=cfg.model,
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
        )

    return _llamar()
