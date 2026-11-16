# football-llm-extractor

Extractor de intenciones futbolísticas con un LLM: convierte una pregunta en lenguaje natural a un JSON validado con **Pydantic** (`equipo`, `temporada`, `metrica`, `condicion`, `es_valida`, `error`).

Compara un **prompt vago** (zero-shot) frente a un **prompt claro + few-shot**, mide tokens/latencia y escribe un CSV de evaluación.

A partir de la **semana 2**, el mismo repo incluye un asistente con **function calling + RAG**: cifras vía `get_team_stats` sobre un CSV ficticio, conceptos vía Chroma sobre el diccionario de datos, y «sin evidencia» fuera del corpus.

## Proveedor LLM

Por defecto usa **Google Gemini (Free Tier)** a través del SDK compatible con OpenAI.

- Docs Gemini OpenAI-compat: https://ai.google.dev/gemini-api/docs/openai
- Modelo por defecto: `gemini-3.5-flash-lite` (si `gemini-2.5-flash-lite` da 404 en cuentas nuevas, use este o `gemini-flash-lite-latest`)
- Para OpenAI de pago: edite solo `.env` (`LLM_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`). El código de `src/client.py` no cambia.

## Requisitos

- Python 3.10+
- Dependencias en `requirements.txt`: `openai`, `pydantic`, `python-dotenv`, `tenacity`, `chromadb`, `sentence-transformers`

## Instalación

```bash
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Linux / macOS
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edite .env y pegue OPENAI_API_KEY (Google AI Studio)
```

**Seguridad:** la clave vive en `.env` (ignorado por Git). Sube a GitHub solo `.env.example` (sin secretos). `chroma_db/` también está en `.gitignore`.

## Uso CLI · Semana 1

```bash
# Extracción de una pregunta (prompt claro por defecto)
python main.py "¿Cuántos goles marcó el Betis en casa en la 2023/24?"

# Prompt vago / mock offline
python main.py "¿Cuántos goles marcó el Málaga en casa?" --prompt vago
python main.py "¿Cuántos goles marcó el Betis en casa en la 2023/24?" --mock

# Primera llamada mínima a Gemini
python prueba_minima.py

# Evaluación del dataset (10×2 llamadas ≈ 20)
python -m src.evaluate
python -m src.evaluate --mock
```

## Semana 2 · Function calling + RAG

Asistente CLI con dos herramientas:

| Ruta | Cuándo | Cómo |
|------|--------|------|
| `funcion` | Preguntas numéricas | `get_team_stats` + Pydantic + CSV ficticio |
| `rag` | Definiciones / reglas | `buscar_documentacion` (Chroma top-3) + citas |
| `sin_evidencia` | Fuera del corpus | Frase fija (umbral de distancia / guardarraíl) |

**Idea clave:** las cifras salen de funciones (o SQL), nunca de una búsqueda por similitud. El RAG sirve para definiciones; el vector store puede devolver texto *parecido*, no necesariamente *correcto* para un número.

### Datos e índice

```bash
python scripts/generar_partidos.py
python -m src.rag_tools.vector_store --mock
python -m src.rag_tools.vector_store --probar "¿Cómo se normaliza el formato de una temporada?"
```

### Preguntar

```bash
python -m src.rag_tools.agente --mock "¿Cuántos puntos sumó el Betis en la temporada 2023/24?"
python -m src.rag_tools.agente --mock "¿Cómo se calculan los puntos de un equipo?"
python -m src.rag_tools.agente --mock "¿Quién ganó el Mundial de 2010?"
python -m src.rag_tools.agente "¿Cuántos puntos sumó el Betis en la temporada 2023/24?"
```

### Evaluación

```bash
python -m src.rag_tools.evaluate_rag --mock
python -m src.rag_tools.evaluate_rag --mock --embeddings real
python -m src.rag_tools.evaluate_rag
```

### Resultados (Gemini real · 16 nov 2026)

| Medida | Valor |
|--------|-------|
| Aciertos numéricas | 5/5 |
| Aciertos conceptuales | 5/5 |
| Aciertos fuera de corpus | 1/1 |
| TOTAL | **11/11** |
| Modelo LLM | `gemini-3.5-flash-lite` |
| Embeddings | `intfloat/multilingual-e5-small` |
| Umbral distancia | `0.15` |
| Llamadas LLM | 21 |
| Tokens | 12 999 |
| Latencia mediana | 7 836 ms |

Por qué e5-small: multilingüe, entrenado para retrieval (prefijos `query:` / `passage:`), y deja una franja clara entre preguntas dentro y fuera del corpus para calibrar el umbral.

Mock de referencia (no usar como resultado de portfolio):

| Comando | Numéricas | Conceptuales | Fuera |
|---------|-----------|-------------:|------:|
| `--mock` (LLM + hash) | 5/5 | 4/5 | 1/1 |
| `--mock --embeddings real` | 5/5 | 5/5 | 1/1 |

## Estructura

```
football-llm-extractor/
├── main.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── data/
│   ├── preguntas.csv
│   ├── partidos_ejemplo.csv
│   └── preguntas_semana2.csv
├── docs/
│   └── diccionario_datos.md
├── scripts/
│   └── generar_partidos.py
├── src/
│   ├── config.py, client.py, models.py, prompts.py, extractor.py, evaluate.py
│   └── rag_tools/
│       ├── stats.py, tools.py, chunking.py, embeddings.py
│       ├── vector_store.py, llm.py, agente.py, evaluate_rag.py
├── tests/
│   ├── test_models.py, test_extractor_mock.py
│   ├── test_rag_stats.py, test_rag_retrieval.py, test_rag_agente.py
├── chroma_db/          # generado; en .gitignore
└── results/
    └── .gitkeep
```

## Checklist · Semana 1

1. Corre como script (`main.py` / `python -m src.evaluate`), no como notebook.
2. La clave vive en `.env`; `.env` está en `.gitignore`; existe `.env.example`.
3. Devuelve JSON validado por Pydantic; errores de parseo/validación quedan marcados.
4. Compara prompt vago vs claro con 2 few-shots y escribe CSV con tokens y latencia.
5. Timeout + rate limit con reintentos (`tenacity`) están implementados.
6. Hay 10 preguntas CSV incluyendo trampas (sin temporada, ambiguo, no fútbol, jugador).
7. README claro y repo en GitHub bajo `miguelASL`.
8. Puede explicar qué es una alucinación aquí: afirmar con seguridad un dato (p.ej. temporada) que no estaba en la pregunta.

## Checklist · Semana 2

1. `get_team_stats` tipada y validada con Pydantic; errores vuelven como mensaje tool.
2. Bucle completo: pregunta → tool_call → validación/ejecución → role=tool → respuesta.
3. Diccionario 20–30 fragmentos en Chroma con embeddings multilingües justificables.
4. Conceptuales: top-3 con fuente y cita entre corchetes.
5. 5 numéricas por función; 5 conceptuales con origen; 1 fuera → sin evidencia.
6. `evaluate_rag` con `--mock` y API real; pytest en verde.
7. README con resultados reales de Gemini; repo sin `.env` ni `chroma_db/`.

## Limitaciones

- Semana 1 no consulta un warehouse: solo **extrae intención**.
- Semana 2 responde con un CSV **ficticio** de ejemplo (semilla fija), no con datos oficiales.
- `json_object` / tool schemas no sustituyen la validación Pydantic.
- El free tier de Gemini tiene rate limits (RPM/RPD); use reintentos, `--pausa` o `--mock`.

## Tests

```bash
pip install pytest
pytest -q
```
