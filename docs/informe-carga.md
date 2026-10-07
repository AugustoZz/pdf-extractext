# Informe: Test de carga, estrés y optimización del extractor-service

## 1. Arquitectura

```
cliente (k6 / Vegeta) ──► extractor-lb (nginx, least_conn) ──► extractor × 5 réplicas
```

- **extractor-lb:** reparte las peticiones con `least_conn`, porque el tiempo de
  procesamiento varía mucho según el PDF.
- **extractor:** FastAPI + uvicorn, sin estado. La extracción a Markdown (PyMuPDF con un
  conversor propio y liviano) corre en un pool de procesos separado del event loop. Un
  control de admisión deja procesar un PDF por vez por réplica (1 CPU) y responde 503 si
  una petición espera más de `QUEUE_TIMEOUT_S`.

Decisiones de diseño (cada una justificada con mediciones en la sección 4):

| Decisión | Por qué |
|---|---|
| nginx con `least_conn`, `proxy_request_buffering off` y buffer de 256 KB | Con PDFs de varios MB, la configuración por defecto convertía al balanceador en el cuello de botella (Experimento 0). |
| Extracción en un pool de procesos | La extracción es CPU-bound: en el event loop bloqueaba hasta `/health` (Experimento 1). |
| 503 tras una espera máxima | Procesar peticiones que el cliente ya abandonó es CPU tirada (Experimento 1). |
| El lugar se toma antes de leer el body | Las peticiones en espera no ocupan memoria con su PDF. |
| PyMuPDF con Markdown propio, no pypdf ni pymupdf4llm | Con los PDFs oficiales es entre 10 y 20 veces más rápido y sigue dando Markdown (Experimentos 2 y 3). |
| PDF crudo en el body | Es lo que envían los scripts del profesor; evita el costo del multipart. |

## 2. Entorno de medición

| | |
|---|---|
| Host | Intel Core i5-8365U (notebook, 4 núcleos / 8 hilos, 1,6 GHz base), 15,8 GB de RAM, Windows 11 Pro |
| Docker | Docker Desktop 29.8.2 (VM con 8 CPUs y 7,6 GB de RAM), Compose 5.5.1 |
| Límites por réplica | 1.0 CPU, 1 GB RAM |
| Balanceador | nginx 1.27, 1.0 CPU, 512 MB RAM |
| Resto del sistema | api (documents-service) 0,5 CPU / 512 MB y MongoDB 0,5 CPU / 1 GB; ociosos durante las pruebas |
| Generadores de carga | k6 y Vegeta sin límites: no son el sistema medido, y limitarlos falsearía las mediciones |
| Réplicas | 5 |
| PDFs | `tests/stress/pdfs` (set oficial de la cátedra) |

Los límites suman 6 CPUs (5 réplicas + nginx) sobre 4 núcleos físicos, y los
generadores de carga corren en el mismo host: bajo carga máxima todos compiten por
CPU, así que los números dependen de este hardware.

## 3. Resultados

Con los 4 PDFs oficiales. Los números del profesor son de su máquina; los nuestros, del
entorno de la sección 2.

### k6, spike (modelo cerrado)

| Versión | Peticiones | req/s | Error | p50 | p95 | Máx |
|---|---|---|---|---|---|---|
| Profesor | 1.037 | 25,35 | 0,00 % | 1,88 s | 8,80 s | 13,94 s |
| Antes: base (pypdf, sin backpressure) | 107 | 1,54 | 14,01 % | 19,22 s | 59,99 s | 59,99 s |
| **Después: final** | 654 | **15,70** | 3,66 % | **4,84 s** | **10,12 s** | 20,01 s |

### Vegeta, carga fija a 50 req/s (modelo abierto)

| Versión | req/s efectivas | Éxito | Timeouts | 503 | p50 |
|---|---|---|---|---|---|
| Profesor | 16,65 | 66,53 % | 33,40 % | — | 14,89 s |
| Antes: base (pypdf, sin backpressure) | 0,65 | 2,60 % | 97,40 % | 0 | 30,00 s |
| **Después: final** | **4,36** | **15,20 %** | **1,20 %** | 83,60 % | 20,01 s |

La versión final multiplica por 10 el throughput de k6 y casi elimina los timeouts de
Vegeta, pero en este hardware no alcanza al profesor (ver sección 5). En k6 los
resultados varían entre corridas: una repetición dio 11,12 req/s con 7,50 % de error
(Experimento 4).

## 4. Proceso de investigación

Un experimento por cambio, medido con los mismos scripts.

Hubo dos etapas. En la primera (Experimentos 0 a 2) todavía no teníamos los PDFs oficiales y
medimos con PDFs sintéticos o provisorios (los de la consigna, de 122 y 172 KB). Al llegar
el set oficial (Experimento 3) los resultados cambiaron mucho: los PDFs livianos nos
habían dado una imagen demasiado optimista, y una decisión (pymupdf4llm) tuvo que
revertirse. Lo dejamos documentado porque es parte del proceso: **hay que medir con la
carga real**.

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
- **Conclusión (provisoria):** se mantenía con estos PDFs; el Experimento 3 la revierte.

### Experimento 3: medición con los PDFs oficiales

Set oficial: Scrum Guide (0,3 MB, 16 págs.), Kanban (8,5 MB, 90 págs.), Filosofía Lean
(0,6 MB, 42 págs.) y Scrum Manager (3,7 MB, 62 págs.).

**Tiempo por PDF** (mediana de 5 extracciones en un solo hilo):

| Opción | Scrum Guide | Kanban | Filosofía Lean | Scrum Manager | Promedio | Markdown |
|---|---|---|---|---|---|---|
| pypdf | 1.993 ms | 5.423 ms | 1.922 ms | 5.060 ms | 3.600 ms | No |
| pymupdf4llm (Experimento 2) | 837 ms | 3.909 ms | 2.449 ms | 3.069 ms | 2.566 ms | Sí |
| pymupdf4llm sin detectar títulos | 1.037 ms | 3.820 ms | 2.318 ms | 2.863 ms | 2.509 ms | Sí |
| PyMuPDF, texto plano | 84 ms | 304 ms | 206 ms | 191 ms | 196 ms | No |
| pypdfium2, texto plano | 111 ms | 360 ms | 206 ms | 310 ms | 247 ms | No |
| **PyMuPDF + Markdown propio** | **90 ms** | **255 ms** | **183 ms** | **179 ms** | **177 ms** | **Sí** |

- Con estos PDFs pymupdf4llm tarda segundos por PDF: con 5 réplicas no llegaría ni a
  2 req/s. El profesor sostiene 25 req/s, o sea ~0,2 s de CPU por petición.
- **Cambio:** un conversor propio sobre `page.get_text("dict")` de PyMuPDF. Cada bloque de
  texto es un párrafo; el texto 1,5 veces más grande que el cuerpo (el tamaño más usado
  del documento) es título `#`, y 1,2 veces, subtítulo `##`; el texto todo en negrita va
  entre `**`. Tarda menos que el texto plano y entra en el presupuesto del profesor.
  pymupdf4llm deja de ser dependencia, y con él ~64 MB de RAM por proceso.

**Bajo carga**, misma infraestructura, cambiando sólo `extractor/`:

| Versión | Vegeta éxito | Vegeta req/s efectivas | Vegeta timeouts | k6 req/s | k6 error | k6 p50 | k6 p95 |
|---|---|---|---|---|---|---|---|
| Stub (techo de la infraestructura) | 100 % | 49,98 | 0 | 133,18 | 0,00 % | 0,48 s | 1,36 s |
| Base (pypdf) | 2,60 % | 0,65 | 1.461 | 1,54 | 14,01 % | 19,22 s | 59,99 s |
| Backpressure + pypdf | 1,80 % | 0,49 | 28 | 3,62 | 65,00 % | 19,99 s | 24,48 s |
| Backpressure + pymupdf4llm | 2,73 % | 0,77 | 24 | 3,81 | 54,62 % | 19,99 s | 21,99 s |
| **Backpressure + Markdown propio** | **15,20 %** | **4,36** | 18 | **15,70** | **3,66 %** | **4,84 s** | **10,12 s** |

- **Techo de la infraestructura (#25):** con el set oficial, nginx sostiene los 50 req/s de
  Vegeta sin errores y 133 req/s en el spike. El límite está en el extractor.
- Con pypdf o pymupdf4llm el servicio está tan saturado que casi todo termina en 503: el
  backpressure protege a las réplicas pero no puede crear capacidad.
- **Conclusión:** se mantiene el Markdown propio.

### Experimento 4: espera de 25 s antes del 503

- **Hipótesis:** los errores de k6 en la versión final son 503 de peticiones que esperaron
  20 s. Con 25 s (todavía por debajo de los 30 s de timeout de Vegeta) deberían
  desaparecer sin perjudicar a Vegeta.

- **Cambio:** `QUEUE_TIMEOUT_S=25`, sin tocar el código.

| Espera | Vegeta éxito | Vegeta req/s efectivas | k6 req/s | k6 error | k6 p50 | k6 p95 |
|---|---|---|---|---|---|---|
| 20 s (corrida 1) | 15,20 % | 4,36 | 15,70 | 3,66 % | 4,84 s | 10,12 s |
| 20 s (corrida 2) | 15,27 % | 4,44 | 11,12 | 7,50 % | 5,66 s | 20,00 s |
| 25 s | 13,47 % | 3,58 | 6,73 | 20,63 % | 6,02 s | 25,00 s |

- **Resultado:** con 25 s empeoran los dos modelos. Más peticiones esperan cerca del límite
  y terminan igual en 503, ahora más tarde, mientras el servicio ya está al máximo de
  capacidad: esperar más no crea capacidad.
- **Variación entre corridas:** repetir la misma configuración (20 s) dio resultados
  estables en Vegeta (15,2 % y 15,3 %) pero no en k6 (15,7 y 11,1 req/s). En una notebook,
  la temperatura y otros procesos del sistema afectan la CPU disponible: para comparar
  variantes parecidas conviene repetir cada medición varias veces.
- **Conclusión:** se descarta; queda 20 s por defecto.

## 5. Cuello de botella y conclusiones

**El cuello de botella es la CPU.** Con el set oficial, la extracción de un PDF cuesta en
promedio ~0,18 s de CPU con la versión final (era ~3,6 s con pypdf). El techo de la
infraestructura (133 req/s en el spike con el stub) está muy por encima de lo que
consigue el extractor, así que nginx, la red y el generador de carga no son el límite
principal.

En este hardware, además, la CPU disponible es menor que la que suman los límites del
compose: 5 réplicas de 1 CPU más nginx sobre un procesador de notebook de 4 núcleos
físicos, con k6 o Vegeta corriendo en la misma máquina. Bajo Vegeta se nota más: mover
~170 MB/s de PDFs le quita CPU a las réplicas. Por eso nuestros números no son
directamente comparables con los del profesor, medidos en su máquina; la comparación
justa es correr las dos versiones en el mismo equipo.

Lo que logramos, medido en el mismo hardware y con el set oficial:

- **k6:** de 1,54 a 15,70 req/s (×10), con la mediana de 19,2 s a 4,8 s.
- **Vegeta:** los timeouts pasan de 97 % a ~1 %. Las peticiones que no se pueden atender
  reciben 503 a los pocos segundos en vez de colgarse hasta el timeout, y las réplicas
  se recuperan al instante en vez de quedar procesando trabajo abandonado.
- **Salida:** `content` en Markdown (títulos, párrafos, negritas) y no texto plano.

Lo que más pesó, en orden: cambiar la librería y la forma de generar el Markdown
(Experimentos 2 y 3), sacar la extracción del event loop con rechazo temprano
(Experimento 1) y ajustar nginx para PDFs grandes (Experimento 0).

Próximos pasos posibles, todos medibles con los mismos scripts: variar la cantidad de
réplicas y de workers por réplica según los núcleos del equipo, y medir en un equipo
con más núcleos físicos para separar el límite del hardware del límite del servicio.
