# Diccionario de datos y reglas de métricas

Documento de referencia del proyecto. Describe la tabla ficticia de partidos,
las columnas, los alias de equipos, las condiciones de filtrado y las reglas
de cálculo de cada métrica. Las cifras de partidos son inventadas.

## Tabla partidos ejemplo

La tabla `data/partidos_ejemplo.csv` contiene partidos ficticios de seis equipos
en dos temporadas. Cada fila es un partido con identificador, fecha, equipos y
marcador. No son resultados oficiales; sirven solo para practicar consultas.

## Columna partido id

`partido_id` identifica de forma única cada partido. El formato es
`AAAA-NN`, donde AAAA es el año de inicio de la temporada y NN el número
secuencial del cruce dentro de esa temporada (por ejemplo `2023-01`).

## Columna temporada

La columna `temporada` indica la campaña a la que pertenece el partido.
En el CSV siempre aparece como `YYYY/YY`, por ejemplo `2022/23` o `2023/24`.

## Columna fecha

La columna `fecha` guarda el día del partido en formato ISO `YYYY-MM-DD`.
Las fechas son ficticias y se generan a partir de una fecha de inicio por
temporada más un desplazamiento fijo entre jornadas.

## Columna equipo local

`equipo_local` es el nombre canónico del equipo que juega en su estadio.
Los nombres válidos coinciden con los alias canónicos del proyecto
(Real Betis, Sevilla FC, Málaga CF, Real Madrid, FC Barcelona, Athletic Club).

## Columna equipo visitante

`equipo_visitante` es el nombre canónico del equipo que juega fuera de casa.
Usa los mismos nombres canónicos que `equipo_local`.

## Columna goles local

`goles_local` es un entero no negativo con los goles marcados por el equipo
local en ese partido. En el CSV de ejemplo los valores se generan al azar
dentro de un rango acotado.

## Columna goles visitante

`goles_visitante` es un entero no negativo con los goles marcados por el
equipo visitante. Junto con `goles_local` determina el resultado del partido.

## Formato de temporada

El formato canónico de temporada es `YYYY/YY` (año de inicio / dos dígitos
del año siguiente). Ejemplos válidos: `2022/23`, `2023/24`. También se
aceptan entradas como `2023-2024` o `2023/2024`, que se normalizan a
`2023/24`. Una temporada es coherente si el año final es el siguiente al inicial.

## Alias de equipos

Los alias permiten escribir nombres cortos o coloquiales. Ejemplos:
`Betis` y `Real Betis` → Real Betis; `Barça`, `Barca`, `Barcelona` → FC Barcelona;
`Madrid` → Real Madrid; `Sevilla` → Sevilla FC; `Málaga`/`Malaga` → Málaga CF;
`Athletic` o `Athletic de Bilbao` → Athletic Club. Tras normalizar (minúsculas
y sin tildes) se busca en el diccionario de alias.

## Condición local

Un partido cuenta como local para un equipo cuando ese equipo aparece en
`equipo_local`, es decir, cuando juega en su propio estadio ("en casa").
La condición `local` filtra solo esos partidos.

## Condición visitante

Un partido cuenta como visitante para un equipo cuando ese equipo aparece en
`equipo_visitante`, es decir, cuando juega en el estadio del rival ("fuera de casa").

## Condición global

La condición `global` incluye todos los partidos del equipo en la temporada,
tanto como local como como visitante. Es el valor por defecto de la herramienta
`get_team_stats` si no se indica otra condición.

## Victoria

Hay victoria cuando los goles propios son estrictamente mayores que los goles
del rival en ese partido. Cada victoria suma tres puntos al total del equipo.

## Empate

Hay empate cuando los goles propios son iguales a los goles del rival.
Cada empate suma un punto. Un empate no cuenta como victoria ni como derrota.

## Derrota

Hay derrota cuando los goles propios son estrictamente menores que los goles
del rival. Una derrota aporta cero puntos.

## Puntos

Los puntos se calculan con el sistema de liga: 3 puntos por victoria, 1 por
empate y 0 por derrota. Fórmula: puntos = 3 × victorias + empates.

## Goles a favor

Los goles a favor son la suma de los goles marcados por el equipo en los
partidos filtrados (local, visitante o global). En local se usan `goles_local`;
en visitante, `goles_visitante`.

## Goles en contra

Los goles en contra son la suma de los goles encajados por el equipo en los
partidos filtrados. En local se usan `goles_visitante` del rival; en visitante,
`goles_local` del rival.

## Diferencia de goles

La diferencia de goles es goles a favor menos goles en contra
(diferencia_goles = goles_favor − goles_contra). Un valor positivo indica
que el equipo marcó más de los que encajó en el filtro aplicado.

## Portería a cero

Un equipo deja la portería a cero en un partido cuando no encaja ningún gol,
es decir, cuando sus goles en contra son 0. La métrica `porterias_a_cero`
cuenta cuántos partidos cumplen esa condición.

## Media de goles

La media de goles a favor es goles_favor / partidos, cuando partidos > 0.
Es una métrica derivada; la herramienta `get_team_stats` expone los totales
y el número de partidos para poder calcularla.

## Porcentaje de puntos

El porcentaje de puntos es (puntos obtenidos / (3 × partidos)) × 100 cuando
hay partidos. Representa qué fracción del máximo posible de puntos se ha logrado.

## Herramienta get team stats

La herramienta `get_team_stats(team, season, condicion)` calcula cifras exactas
sobre el CSV: partidos, victorias, empates, derrotas, goles a favor y en contra,
diferencia de goles, porterías a cero y puntos. Valida argumentos con Pydantic
antes de ejecutar. No responde definiciones conceptuales.

## Limitaciones del conjunto de datos

El conjunto no tiene jugadores, tarjetas, posesión, asistencias ni competiciones
europeas. Solo cubre seis equipos y dos temporadas. Los marcadores son ficticios.
Las preguntas fuera de este alcance deben responderse sin evidencia documental.
