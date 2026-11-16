"""Índice vectorial persistente en Chroma + búsqueda top-k con umbral de distancia."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

import chromadb

from src.rag_tools.chunking import trocear_markdown
from src.rag_tools.embeddings import Embedder, crear_embedder

ROOT = Path(__file__).resolve().parents[2]
CHROMA_DIR = ROOT / "chroma_db"  # en .gitignore: se regenera con indexar
COLECCION = "diccionario_futbol"


@dataclass(frozen=True)
class Resultado:
    id: str
    texto: str
    distancia: float  # distancia coseno: 0 = idéntico, cuanto mayor, menos parecido


def umbral_por_defecto(mock: bool) -> float:
    clave = "RAG_UMBRAL_MOCK" if mock else "RAG_UMBRAL_DISTANCIA"
    return float(os.getenv(clave, "0.60" if mock else "0.15"))


def _coleccion(mock: bool, directorio: Path = CHROMA_DIR):
    cliente = chromadb.PersistentClient(path=str(directorio / ("mock" if mock else "real")))
    return cliente.get_or_create_collection(name=COLECCION, metadata={"hnsw:space": "cosine"})


def indexar(mock: bool = False, embedder: Embedder | None = None, directorio: Path = CHROMA_DIR) -> int:
    fragmentos = trocear_markdown()
    emb = embedder or crear_embedder(mock)
    col = _coleccion(mock, directorio)
    col.upsert(  # upsert: re-ejecutar no duplica fragmentos
        ids=[f.id for f in fragmentos],
        documents=[f.texto for f in fragmentos],
        embeddings=emb.documentos([f.texto for f in fragmentos]),
        metadatas=[{"titulo": f.titulo, "modelo": emb.nombre} for f in fragmentos],
    )
    return len(fragmentos)


class Buscador:
    def __init__(
        self,
        mock: bool = False,
        embedder: Embedder | None = None,
        directorio: Path = CHROMA_DIR,
    ) -> None:
        self.mock = mock
        self.embedder = embedder or crear_embedder(mock)
        self.col = _coleccion(mock, directorio)
        if self.col.count() == 0:
            indexar(mock, self.embedder, directorio)

    def buscar(self, consulta: str, k: int = 3) -> list[Resultado]:
        r = self.col.query(query_embeddings=[self.embedder.consulta(consulta)], n_results=k)
        return [
            Resultado(id=i, texto=t, distancia=round(float(d), 4))
            for i, t, d in zip(r["ids"][0], r["documents"][0], r["distances"][0])
        ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Indexa docs/diccionario_datos.md en Chroma")
    parser.add_argument("--mock", action="store_true", help="Embeddings de juguete, sin descargas")
    parser.add_argument("--probar", help="Pregunta de prueba para ver el top-3 y sus distancias")
    args = parser.parse_args()
    n = indexar(mock=args.mock)
    print(f"Indexados {n} fragmentos en {CHROMA_DIR / ('mock' if args.mock else 'real')}")
    if args.probar:
        for r in Buscador(mock=args.mock).buscar(args.probar):
            print(f"{r.distancia:.4f}  {r.id}")


if __name__ == "__main__":
    main()
