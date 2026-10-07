# Informe: Test de carga, estrés y optimización del extractor-service

## 1. Arquitectura

```
cliente (k6 / Vegeta) ──► extractor-lb (nginx, least_conn) ──► extractor × 5 réplicas
```

- **extractor-lb:** reparte las peticiones con `least_conn`, porque el tiempo de
  procesamiento varía mucho según el PDF.
- **extractor:** FastAPI + uvicorn, sin estado. La extracción a Markdown (PyMuPDF vía
  pymupdf4llm, conversor clásico) corre en un pool de procesos separado del event loop. Un control de admisión deja procesar un PDF por vez
  por réplica (1 CPU) y responde 503 si una petición espera más de `QUEUE_TIMEOUT_S`
  (20 s por defecto).

Decisiones de diseño: _(completar a medida que se toman, con su justificación)_

## 2. Entorno de medición

| | |
|---|---|
| Host | Intel Core i5-8365U (notebook, 4 núcleos / 8 hilos, 1,6 GHz base), 15,8 GB de RAM, Windows 11 Pro |
| Docker | Docker Desktop 29.8.2 (VM con 8 CPUs y 7,6 GB de RAM), Compose 5.5.1 |
| Límites por réplica | 1.0 CPU, 1 GB RAM |
| Balanceador | nginx 1.27, 1.0 CPU, 512 MB RAM |
| Réplicas | 5 |
| PDFs | `tests/stress/pdfs` (set oficial de la cátedra) |

Los límites suman 6 CPUs (5 réplicas + nginx) sobre 4 núcleos físicos, y los
generadores de carga corren en el mismo host: bajo carga máxima todos compiten por
CPU, así que los números dependen de este hardware.

## 3. Resultados

### k6, spike (modelo cerrado)

| Versión | Peticiones | req/s | Error | p50 | p90 | p95 | Máx |
|---|---|---|---|---|---|---|---|
| Profesor | 1.037 | 25,35 | 0,00 % | 1,88 s | 7,83 s | 8,80 s | 13,94 s |
| Base (pypdf) | | | | | | | |

### Vegeta, carga fija a 50 req/s (modelo abierto)

| Versión | req/s efectivas | Éxito | Timeouts | p50 |
|---|---|---|---|---|
| Profesor | 16,65 | 66,53 % | 33,40 % | 14,89 s |
| Base (pypdf) | | | | |

## 4. Proceso de investigación

Un experimento por cambio, medido con los mismos scripts.

### Experimento 0: techo de la infraestructura (stub sin procesamiento)

Antes de medir el extractor real se corrió k6 contra un stub que responde sin
procesar el PDF, para saber cuánto cuesta sólo mover los archivos. Se usaron PDFs
sintéticos, no el set oficial, así que los números sirven para comparar
configuraciones entre sí, no contra el profesor.

**Fase A: body multipart** (PDFs de 10 KB, 200 KB, 2 MB y 9 MB), sólo k6:

| Configuración de nginx | req/s | Error | p50 | p95 | Observación |
|---|---|---|---|---|---|
| `keepalive` hacia las réplicas | 13,9 | 4,64 % (502) | 3,66 s | 19,82 s | "Broken pipe": uvicorn cierra las conexiones inactivas a los 5 s y nginx las reutiliza |
| Sin `keepalive` | 15,1 | 0,00 % | 3,38 s | 15,96 s | nginx al 100 % de CPU, réplicas al ~50 % |
| `proxy_request_buffering off` | 33,4 | 0,00 % | 1,59 s | 7,48 s | nginx ya no escribe cada body a disco antes de reenviarlo |

**Fase B: PDF crudo en el body**, como los scripts del profesor (PDFs de 300 KB, 1 MB,
3 MB y 9 MB):

| Configuración de nginx | k6 req/s | k6 error | k6 p95 | Vegeta éxito | Vegeta p50 | Observación |
|---|---|---|---|---|---|---|
| Buffer de lectura 16 KB (defecto) | 31,7 | 0,00 % | 7,77 s | 71,7 % | 17,78 s | nginx al 100 % de CPU: cientos de lecturas por PDF |
| Buffer 1 MB | 37,5 | 2,76 % | 15,20 s | 100 % | 15,9 ms | Vegeta resuelto; bajo k6 nginx supera los 256 MB y el kernel mata workers |
| Buffer 256 KB, 256 MB de RAM | 34,5 | 4,23 % | 20,46 s | 100 % | 5,2 ms | Sigue el OOM bajo 100 conexiones simultáneas |
| **Buffer 256 KB, 512 MB de RAM** | **184,3** | **0,00 %** | **0,91 s** | — | — | Sin OOM; nginx deja de ser el cuello de botella |

- **Conclusión:** con bodies de varios MB, el balanceador era el cuello de botella antes
  que el extractor. La configuración final usa `proxy_request_buffering off`,
  `client_body_buffer_size 256k` y 512 MB de RAM para nginx. `keepalive` queda descartado
  hasta que el extractor use un timeout de keep-alive mayor que el de nginx.
- **Techo de la infraestructura:** ~184 req/s en el spike, siete veces el throughput del
  profesor. A partir de acá el límite lo pone el extractor.
### Ajuste del generador de carga: memoria de k6

k6 corre en el mismo host que el servicio, así que la RAM que usa se la quita a las
réplicas. Con el script original llegaba a casi 4 GB de los 7,6 GB de la VM de Docker.
Medido con el spike completo contra el stub (pico de memoria del contenedor de k6):

| Variante | Pico de RAM | req/s | Error |
|---|---|---|---|
| Script original (`open()` clásico) | 3.932 MiB | 170,1 | 0,00 % |
| PDFs compartidos (`k6/experimental/fs`) | 3.123 MiB | 160,2 | 0,00 % |
| Script original + `GOMEMLIMIT=1GiB` | 2.038 MiB | 205,0 | 0,00 % |
| **PDFs compartidos + `GOMEMLIMIT=1GiB`** | **986 MiB** | 161,2 | 0,00 % |

- **Por qué hacen falta las dos:** el `open()` clásico guarda una copia de los PDFs por VU
  (100 copias, ~1,3 GB siempre vivos), y el recolector de Go deja crecer la memoria al
  doble de lo que se usa antes de liberar. Con los PDFs compartidos queda poco vivo, y
  `GOMEMLIMIT` hace que el recolector lo libere antes.
- **Comparabilidad:** la petición es la misma que la del script del profesor (PDF crudo,
  elegido al azar); sólo cambia cómo k6 guarda los archivos en memoria.
- Las diferencias de req/s entre variantes están dentro de la variación entre corridas
  contra el stub.

### Experimento 1: backpressure (pool de procesos + 503 por saturación)

Medido con PDFs **provisorios** (los dos PDFs de la cátedra, de 122 y 172 KB, rotando como
los 4 oficiales), así que sirve para comparar versiones entre sí, no contra el profesor.

- **Hipótesis:** en la versión base la extracción bloquea el event loop. Bajo sobrecarga
  las peticiones esperan hasta el timeout del cliente y el servicio sigue procesando las
  que el cliente ya abandonó: CPU tirada.
- **Cambio:** la extracción pasa a un `ProcessPoolExecutor`, y un control de admisión
  rechaza con 503 a las peticiones que no consiguen lugar en `QUEUE_TIMEOUT_S`. El lugar
  se toma antes de leer el body, para que las peticiones en espera no ocupen memoria.

| Versión | Vegeta éxito | Vegeta timeouts | Vegeta p50 | Vegeta req/s efectivas | Recuperación tras la prueba | k6 req/s | k6 error | k6 p50 | k6 p95 |
|---|---|---|---|---|---|---|---|---|---|
| Base | 18,3 % (275) | 1.225 | 30,0 s | 4,58 | ~110 s | 7,21 | 0,00 % | 11,45 s | 17,46 s |
| Backpressure, espera 10 s | 19,3 % (290) | 0 | 10,0 s | 7,14 | — | 9,53 | 14,84 % | 9,22 s | 10,70 s |
| **Backpressure, espera 20 s** | **23,7 % (355)** | **0** | 20,0 s | 6,99 | ~5 s | 7,23 | **0,00 %** | 12,05 s | 15,51 s |

- **Resultado:** sin timeouts, 29 % más peticiones exitosas en Vegeta, y las réplicas se
  recuperan al instante: en la base quedaban "unhealthy" (ni `/health` respondía) y
  tardaban ~110 s en vaciar el trabajo abandonado.
- **El tiempo de espera es un compromiso:** con 10 s se rechaza de más y k6 (modelo
  cerrado, sin timeout de 30 s) pasa a tener 15 % de errores. Con 20 s, k6 queda igual que
  la base y Vegeta mejora.
- **Conclusión:** se mantiene, con 20 s por defecto. El throughput total casi no cambia:
  el límite sigue siendo la extracción con pypdf, que es lo que ataca #32.

### Experimento 2: librería de extracción (pypdf → PyMuPDF con salida Markdown)

- **Hipótesis:** con el backpressure, el límite pasó a ser la extracción. pypdf está
  escrita en Python puro; PyMuPDF es una capa sobre MuPDF, escrito en C. Además, la
  consigna pide Markdown y pypdf sólo da texto plano, a veces muy fragmentado (una palabra
  por línea en PDFs exportados de Google Docs).
- **Investigación previa:** mediana de 15 extracciones en un solo hilo, con los PDFs de la
  cátedra.

  | Opción | Consigna (122 KB) | TP (172 KB) | Markdown |
  |---|---|---|---|
  | pypdf | 119 ms | 366 ms | No |
  | PyMuPDF, texto plano | 7 ms | 13 ms | No |
  | pypdfium2, texto plano | 8 ms | 26 ms | No |
  | **pymupdf4llm clásico, sin tablas/imágenes/gráficos** | **44 ms** | **169 ms** | **Sí** |
  | pymupdf4llm clásico, completo | 612 ms | 1.632 ms | Sí, con tablas |
  | pymupdf4llm 1.28 por defecto (modelo de layout) | 789 ms | 1.897 ms | Sí |

  El texto plano de PyMuPDF es el más rápido, pero no cumple con el Markdown. Detectar
  tablas es más del 90 % del costo, y el modo por defecto de pymupdf4llm 1.28 usa un
  modelo de IA para el layout, que es lo más lento de todo.
- **Cambio:** pymupdf4llm con `use_layout(False)` y sin tablas, imágenes ni gráficos.
  Importarlo suma ~64 MB por proceso (el paquete del modelo es dependencia obligatoria
  aunque no se use). PyMuPDF tiene licencia AGPL.

| Versión | Vegeta éxito | Vegeta req/s efectivas | k6 req/s | k6 error | k6 p50 | k6 p95 | k6 máx |
|---|---|---|---|---|---|---|---|
| Backpressure + pypdf | 23,7 % (355) | 6,99 | 7,23 | 0,00 % | 12,05 s | 15,51 s | 17,22 s |
| **Backpressure + PyMuPDF** | **61,1 % (916)** | **18,21** | **20,18** | **0,00 %** | **4,31 s** | **5,81 s** | **6,48 s** |

- **Resultado:** ~2,8 veces más throughput en los dos modelos de carga y latencias divididas
  por tres, sin errores en k6 ni timeouts en Vegeta. Cada réplica usa ~170 MB de su 1 GB.
- **Calidad:** el contenido pasa a ser Markdown real (títulos, negritas, párrafos).
- **Conclusión:** se mantiene.

### Experimento N: _(título)_

- **Hipótesis:**
- **Cambio:**
- **Resultado:** _(métricas antes / después)_
- **Conclusión:** _(se mantiene o se descarta, y por qué)_

## 5. Cuello de botella y conclusiones

_(completar)_
