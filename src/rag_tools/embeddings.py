"""Embeddings reales (e5-small) y mock (hash bag-of-words) para --mock y tests."""

from __future__ import annotations

import hashlib
import math
import os
import re
import unicodedata
from typing import Protocol

MODELO_POR_DEFECTO = "intfloat/multilingual-e5-small"

_STOPWORDS = set(
    "el la los las un una de del al a en y o que qué es se por para con como cómo "
    "su sus mi tus le les lo me te nos os un una unos unas al del si no ya "
    "cuando cuándo cuantos cuántos cuantas cuántas cual cuál cuales cuáles "
    "donde dónde quien quién quienes quiénes hay hayn ser estar".split()
)


class Embedder(Protocol):
    nombre: str

    def documentos(self, textos: list[str]) -> list[list[float]]: ...

    def consulta(self, texto: str) -> list[float]: ...


def _tokens(texto: str) -> list[str]:
    normal = unicodedata.normalize("NFKD", texto.lower())
    limpio = "".join(c for c in normal if not unicodedata.combining(c))
    return [t for t in re.findall(r"[a-z0-9]+", limpio) if t not in _STOPWORDS and len(t) > 2]


class HashEmbedder:
    """Embedding de juguete (bolsa de palabras con hash). Sin descargas: para --mock y tests."""

    nombre = "hash-bow-256 (mock)"

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def _vector(self, texto: str) -> list[float]:
        v = [0.0] * self.dim
        for tok in _tokens(texto):
            raiz = tok[:5]  # "raíz" muy tosca: goles/gol, visitante/visitantes
            v[int(hashlib.md5(raiz.encode()).hexdigest(), 16) % self.dim] += 1.0
        norma = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norma for x in v]

    def documentos(self, textos: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in textos]

    def consulta(self, texto: str) -> list[float]:
        return self._vector(texto)


class SentenceTransformerEmbedder:
    """Embeddings locales con sentence-transformers (se descargan una vez, ~470 MB)."""

    def __init__(self, nombre: str = MODELO_POR_DEFECTO) -> None:
        from sentence_transformers import SentenceTransformer  # import perezoso: es pesado

        self.nombre = nombre
        self._modelo = SentenceTransformer(nombre)
        # La familia E5 se entrenó con prefijos: sin ellos, la búsqueda empeora.
        self._es_e5 = "e5" in nombre.lower()

    def _codificar(self, textos: list[str]) -> list[list[float]]:
        vectores = self._modelo.encode(textos, normalize_embeddings=True)
        return [v.tolist() for v in vectores]

    def documentos(self, textos: list[str]) -> list[list[float]]:
        if self._es_e5:
            textos = [f"passage: {t}" for t in textos]
        return self._codificar(textos)

    def consulta(self, texto: str) -> list[float]:
        return self._codificar([f"query: {texto}" if self._es_e5 else texto])[0]


def crear_embedder(mock: bool) -> Embedder:
    if mock:
        return HashEmbedder()
    return SentenceTransformerEmbedder(os.getenv("EMBEDDING_MODEL", MODELO_POR_DEFECTO))
