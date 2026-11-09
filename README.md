# football-llm-extractor

Extractor de intenciones futbolísticas con un LLM: convierte una pregunta en lenguaje natural a un JSON validado con **Pydantic** (`equipo`, `temporada`, `metrica`, `condicion`, `es_valida`, `error`).

Compara un **prompt vago** (zero-shot) frente a un **prompt claro + few-shot**, mide tokens/latencia y escribe un CSV de evaluación.

## Proveedor LLM

Por defecto usa **Google Gemini (Free Tier)** a través del SDK compatible con OpenAI.

- Docs Gemini OpenAI-compat: https://ai.google.dev/gemini-api/docs/openai
- Modelo por defecto: `gemini-3.5-flash-lite` (si `gemini-2.5-flash-lite` da 404 en cuentas nuevas, use este o `gemini-flash-lite-latest`)
- Para OpenAI de pago: edite solo `.env` (`LLM_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`). El código de `src/client.py` no cambia.

## Requisitos

- Python 3.10+
- Dependencias en `requirements.txt`: `openai`, `pydantic`, `python-dotenv`, `tenacity`

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

**Seguridad:** la clave vive en `.env` (ignorado por Git). Sube a GitHub solo `.env.example` (sin secretos).

## Uso CLI

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

## Estructura

```
football-llm-extractor/
├── main.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── data/preguntas.csv
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── models.py
│   ├── prompts.py
│   ├── client.py
│   ├── extractor.py
│   └── evaluate.py
├── tests/
│   ├── test_models.py
│   └── test_extractor_mock.py
└── results/
    └── .gitkeep
```

## Checklist · hecho cuando…

1. Corre como script (`main.py` / `python -m src.evaluate`), no como notebook.
2. La clave vive en `.env`; `.env` está en `.gitignore`; existe `.env.example`.
3. Devuelve JSON validado por Pydantic; errores de parseo/validación quedan marcados.
4. Compara prompt vago vs claro con 2 few-shots y escribe CSV con tokens y latencia.
5. Timeout + rate limit con reintentos (`tenacity`) están implementados.
6. Hay 10 preguntas CSV incluyendo trampas (sin temporada, ambiguo, no fútbol, jugador).
7. README claro y repo en GitHub bajo `miguelASL`.
8. Puede explicar qué es una alucinación aquí: afirmar con seguridad un dato (p.ej. temporada) que no estaba en la pregunta.

## Limitaciones

- No consulta un warehouse / base de datos real todavía: solo **extrae intención**, no responde con cifras verificadas.
- `json_object` garantiza JSON válido, no que las claves cumplan el esquema: por eso validamos con Pydantic.
- El free tier de Gemini tiene rate limits (RPM/RPD); use reintentos o `--mock`.

## Tests

```bash
pip install pytest
pytest -q
```
