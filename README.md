# football-llm-extractor

Extractor de intenciones futbolísticas con LLM + **servidor MCP** (`src/mcp_server`) que expone tools/resources/prompts sobre datos **ficticios** de partidos.

## Checklist de verificación (semana 3 · MCP)

| Prueba | Resultado |
| --------------------------------------------- | ----------------------- |
| Tools listadas en Inspector | OK: `get_team_stats`, `buscar_documentacion` |
| Llamada válida (Betis 2023/24) | OK: `isError: false`, Real Betis, **19 puntos** |
| Entrada inválida → isError: true | OK: `Atlético` → `Equipo desconocido` + lista de válidos |
| Lo que falló con Inspector y cómo lo resolvió | Ver sección abajo |
| Host con Gemini real (opcional) | OK: responde 19 puntos vía `get_team_stats` |
| pytest -q | OK: **17 passed** |

### Lo que falló con Inspector y cómo se resolvió

1. **`ModuleNotFoundError: No module named 'src.mcp_server'`**  
   La carpeta se llamaba `mcp_servclear` (typo). Se renombró a `src/mcp_server` y se añadió `__init__.py`.

2. **`FileNotFoundError: data/partidos_ejemplo.csv`**  
   Faltaban datos y código de `src/rag_tools/`. Se restauraron desde la rama `semana2-rag-tools`.

3. **Ruta Unix en Windows**  
   Los ejemplos usaban `.venv/bin/python`. En Windows hay que usar `.\.venv\Scripts\python.exe`.

4. **Import `mcp` no resuelto en el IDE**  
   El paquete estaba en el `.venv`, pero Pylance no lo usaba. Se configuró el intérprete (`.vscode/settings.json` + `pyrightconfig.json`).

## Inspector CLI (Windows PowerShell)

```powershell
# Listar tools
npx @modelcontextprotocol/inspector --cli -e FUTBOL_MCP_MOCK=1 .\.venv\Scripts\python.exe -m src.mcp_server.server --method tools/list

# Llamada válida
npx @modelcontextprotocol/inspector --cli -e FUTBOL_MCP_MOCK=1 .\.venv\Scripts\python.exe -m src.mcp_server.server --method tools/call --tool-name get_team_stats --tool-arg team=Betis --tool-arg season=2023/24

# Entrada inválida (isError: true)
npx @modelcontextprotocol/inspector --cli -e FUTBOL_MCP_MOCK=1 .\.venv\Scripts\python.exe -m src.mcp_server.server --method tools/call --tool-name get_team_stats --tool-arg team=Atlético --tool-arg season=2023/24

# UI del Inspector
npx @modelcontextprotocol/inspector -e FUTBOL_MCP_MOCK=1 .\.venv\Scripts\python.exe -m src.mcp_server.server
```

## Host Gemini + MCP (opcional)

```powershell
# Mock (sin clave)
.\.venv\Scripts\python.exe -m src.mcp_server.host_gemini "¿Cuántos puntos tiene el Betis en la 2023/24?" --mock

# Gemini real (usa OPENAI_API_KEY de .env)
.\.venv\Scripts\python.exe -c "from dotenv import load_dotenv; load_dotenv(); from src.mcp_server.host_gemini import responder; import asyncio, json; print(json.dumps(asyncio.run(responder('¿Cuántos puntos tiene el Betis en la 2023/24?', mock=False, embeddings_mock=True)), ensure_ascii=False, indent=2))"
```

Ejemplo observado con Gemini real:

- Tool: `get_team_stats` · `team=Real Betis` · `season=2023/24` · `is_error=false`
- Respuesta: *El Real Betis tiene 19 puntos en la temporada 2023/24…*

## Instalación

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
# Pegue OPENAI_API_KEY (Google AI Studio) en .env
```

Dependencias clave: `openai`, `pydantic`, `python-dotenv`, `tenacity`, `mcp[cli]==2.3.0`, `pytest`.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Estructura (MCP)

```
src/mcp_server/
  server.py        # MCPServer: tools, resources, prompts (stdio)
  host_gemini.py   # Host mínimo: Gemini ↔ call_tool MCP
src/rag_tools/     # stats, vector_store, agente, llm…
data/partidos_ejemplo.csv
tests/test_mcp_server.py
```

## Limitaciones

- Datos **ficticios** (CSV de ejemplo), no una liga real.
- Con stdio, los logs van a **stderr**; stdout es solo JSON-RPC.
- `FUTBOL_MCP_MOCK=1` evita descargar embeddings (útil en Inspector/tests).
