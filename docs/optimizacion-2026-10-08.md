# Optimización y validación de carga — 08/10/2026

> **Actualización:** las cifras siguientes corresponden a HTTP interno.
> Las [corridas por el gateway Windows](carga-corregida-2026-10-08.md) dieron resultados bajos.
> Las [últimas corridas por los puertos del host Linux](carga-host-linux-2026-10-08.md),
> con HTTPS y límites de generadores, dieron 37,67–38,17 req/s en k6 y 100 % de éxito en Vegeta.

La versión optimizada completó las 1.500 solicitudes de Vegeta con HTTP 200 en
dos corridas consecutivas. El throughput efectivo pasó de 7,36 a 26,84–26,94 req/s
en esta misma PC. En k6 pasó de 31,91 a 35,20–35,26 req/s, con cero errores.
Se superan los valores de referencia del profesor en throughput de ambos tests,
éxito de Vegeta, mediana de Vegeta y p95 de k6. La mediana de k6 del profesor
sigue siendo menor. Su equipo es distinto: esta comparación no sustituye una
evaluación de ambas implementaciones en el mismo hardware ni garantiza el
puntaje extra.

## Auditoría de las condiciones solicitadas

Esta sección describe las salvedades de las primeras mediciones. Se corrigieron
mediante el complemento TLS y los límites de los generadores; los resultados
posteriores se encuentran en el [informe actualizado](carga-corregida-2026-10-08.md).

Se conservaron los perfiles, los cuatro PDFs, el body binario, el chequeo de
HTTP 200, el timeout de Vegeta y los límites del sistema medido. Hay dos
salvedades que impiden afirmar igualdad completa con la ejecución del profesor:

- Los contenedores de k6 y Vegeta no tienen límites Docker de CPU/RAM.
  `GOMEMLIMIT` ajusta el recolector de Go y no es un límite de contenedor.
  Se consideraron herramientas externas al sistema medido, pero la consigna
  dice que cada contenedor/instancia debe tener recursos explícitos. Bajo esa
  lectura literal, falta cubrir este punto y repetir las mediciones con esa
  configuración.
- El script original de k6 apunta a `https://extract.universidad.localhost`;
  se ejecutó contra `http://extractor-lb` en la red interna de Docker. Vegeta
  pasó de `http://localhost:8080` a esa misma dirección interna. Se eliminó
  TLS en k6 y se evitó el recorrido por el puerto publicado del host. La
  consigna permite adaptar los scripts; este cambio no altera los perfiles,
  pero sí importa para comparar las latencias y throughput con el profesor.

El antes/después en esta PC usó la misma dirección interna y sigue siendo una
comparación local consistente. Los resultados actuales no demuestran igualdad
de protocolo y recorrido de red con los valores de la cátedra.

El criterio del extra, en la página 3 de la consigna, pide mayor throughput de
k6 y mejor tasa de éxito y latencias en Vegeta bajo las mismas restricciones de
hardware. No exige explícitamente que la mediana de k6 sea menor. Las cifras
medidas superan esos valores de referencia, pero la concesión del puntaje no
puede asegurarse con las salvedades anteriores. El primer puesto requiere
comparación con las demás entregas. Los cambios también deben publicarse en los
repositorios para que la entrega incluya la versión medida.

## Resultados verificables

Las latencias de k6 están en milisegundos en sus JSON; las de Vegeta, en
nanosegundos. Aquí se convierten a segundos. El throughput de Vegeta incluye
el tiempo necesario para recibir las respuestas pendientes después del ataque;
no equivale a la tasa de envío configurada de 50 req/s.

| k6 | Antes, esta PC | Final 1 | Final 2 | Profesor |
|---|---:|---:|---:|---:|
| Solicitudes | 1.281 | 1.409 | 1.415 | 1.037 |
| Throughput, req/s | 31,90676 | 35,19688 | 35,25581 | 25,35 |
| Errores | 0 % | 0 % | 0 % | 0 % |
| Mediana, s | 2,76370 | 2,54883 | 2,48032 | 1,88 |
| p95, s | 3,54590 | 3,06624 | 3,15646 | 8,80 |

| Vegeta | Antes, esta PC | Final 1 | Final 2 | Profesor |
|---|---:|---:|---:|---:|
| Solicitudes enviadas | 1.500 | 1.500 | 1.500 | 1.500 |
| Throughput efectivo, req/s | 7,36208 | 26,93508 | 26,84375 | 16,65 |
| Éxito | 29,40 % | 100 % | 100 % | 66,53 % |
| Mediana, s | 26,82565 | 8,60958 | 9,08218 | 14,89 |
| p95, s | 30,00110 | 16,99600 | 17,59990 | — |

Antes, Vegeta registró 441 respuestas 200, 433 respuestas 503, 40 respuestas 502
y 586 errores con código 0. Código 0 comprende errores de transporte y timeout;
no todos son timeouts. En cada corrida final hubo 1.500 respuestas 200, cero
503, cero 502 y cero errores de transporte o timeout. El mayor tiempo observado
fue 29,14861 s en la primera y 28,02292 s en la segunda; no se incrementó el
timeout de 30 s.

Evidencia original:

- Antes: [k6](../output/carga-profesor-2026-10-08/profesor-k6.json) y
  [Vegeta](../output/carga-profesor-2026-10-08/profesor-vegeta.json).
- Final 1: [k6 JSON](../output/optimizacion/final-1/optimizado-k6.json),
  [dashboard](../output/optimizacion/final-1/optimizado-k6.html),
  [Vegeta JSON](../output/optimizacion/final-1/profesor-vegeta.json),
  [binario](../output/optimizacion/final-1/profesor-vegeta.bin) y
  [gráfico](../output/optimizacion/final-1/profesor-vegeta.html).
- Final 2: [k6 JSON](../output/optimizacion/final-2/optimizado-k6.json),
  [dashboard](../output/optimizacion/final-2/optimizado-k6.html),
  [Vegeta JSON](../output/optimizacion/final-2/profesor-vegeta.json),
  [binario](../output/optimizacion/final-2/profesor-vegeta.bin) y
  [gráfico](../output/optimizacion/final-2/profesor-vegeta.html).

Los valores del profesor son los publicados en la consigna y transcritos en el
[informe previo del extractor](https://github.com/valendotjpg/pdf-extractext-extractor/blob/main/docs/informe-carga.md).
Los archivos de `output/` son evidencia local; deben conservarse junto al informe
o adjuntarse a la entrega para que esos enlaces funcionen fuera de esta PC.

## Qué cambió y por qué

Se separó la recepción del PDF de su procesamiento. Antes, una solicitud obtenía
el único slot de CPU y luego recibía su archivo. Las demás esperaban sin consumir
su body, bloqueando las transferencias. Uvicorn confirma que pausa la lectura del
transporte cuando el buffer alcanza su límite y la aplicación no recibe datos.
[Documentación de Uvicorn](https://www.uvicorn.org/server-behavior/).

Ahora cada réplica admite hasta 32 uploads o PDFs pendientes. El archivo se recibe
en memoria con límite de 10 MiB; solamente después se toma el slot de CPU.
Esto permite recibir un PDF mientras se extrae el anterior. El cupo de ingreso
permanece reservado hasta terminar, por lo que los PDFs retenidos suman como
máximo 320 MiB por réplica, además de buffers temporales, runtime y proceso de
extracción. Cada una de las dos etapas puede esperar hasta 20 s por su cupo:
ese valor no es un límite total de latencia de la petición.

El conversor conserva por bloque sólo texto, tamaño máximo y condición de negrita,
y procesa los spans una vez. Ya no retiene el árbol completo de geometría y
fuentes de todas las páginas. Se mantuvieron las reglas de Markdown, el contenido
y el número de páginas; la validación sobre los cuatro PDFs confirmó igualdad de
los hashes de salida antes y después. Cada petición sigue extrayéndose: no se
incorporó una caché de resultados ni se omitió procesamiento en el benchmark.

La [medición individual y hashes de salida](../output/extraction_cpu_measurements.json)
usó un calentamiento y siete extracciones independientes por PDF, con 1 CPU y
1 GiB. Las medianas muestran una mejora pequeña de CPU; el salto de Vegeta se
explica principalmente por separar transferencia y procesamiento:

| PDF | Antes, ms | Optimizado, ms |
|---|---:|---:|
| Scrum Guide | 37,373 | 36,603 |
| Kanban | 133,466 | 131,797 |
| Filosofía Lean | 88,366 | 86,305 |
| Scrum Manager | 89,944 | 83,530 |

Nginx utiliza un worker, coherente con su límite de 1 CPU, `least_conn`, estado
compartido del upstream, streaming del body y conexiones reutilizables. Su
keepalive de 30 s vence antes del de Uvicorn, configurado en 60 s, para evitar
reutilizar conexiones ya cerradas. También se desactivó el log de acceso del
extractor en el despliegue de carga.
[Documentación de nginx](https://nginx.org/en/docs/http/ngx_http_upstream_module.html).

La extracción continúa en `ProcessPoolExecutor`, con un worker por réplica.
PyMuPDF no admite uso concurrente multihilo; su documentación recomienda
procesos separados. [Documentación de PyMuPDF](https://pymupdf.readthedocs.io/en/latest/recipes-multiprocessing.html).

## Condiciones y reproducción

Se conservaron cinco réplicas, cada una con 1 CPU y 1 GiB, y nginx con 1 CPU y
512 MiB. Los generadores corren en Docker en la misma PC, sin límites propios;
`GOMEMLIMIT=1GiB` de k6 se mantuvo en las corridas antes y después. Los cuatro
PDFs oficiales fueron los mismos, verificados con SHA-256; no se publican aquí
por ser material de terceros.

Se utilizaron `spike_tests.js` y `test_carga.txt` del profesor, adaptando únicamente
URL y rutas a los archivos. k6 mantiene etapas de 10/20/10 s y pico de 100 VUs.
Vegeta mantiene 50 req/s durante 30 s y timeout de 30 s. La selección aleatoria
de k6 puede variar entre corridas; no se fijó una distribución favorable.

Para levantar el proyecto completo con la copia local optimizada, desde la raíz:

```powershell
$env:EXTRACTOR_BUILD_CONTEXT = './.test-extractor'
docker compose up --build -d
```

La carpeta `.test-extractor` debe existir con estos cambios. En esta PC, `.env`
también selecciona esa carpeta. Sin `EXTRACTOR_BUILD_CONTEXT` en el entorno ni
en `.env`, Compose construye desde el repositorio remoto: la optimización debe
incorporarse allí para que un clon nuevo la obtenga automáticamente.

Estos cambios son locales y todavía no están publicados. La copia parte del
commit `236829facd728b0216f421f2598e0c9d3598fbd8` del repositorio del extractor.
Se prepararon un [patch](../output/optimizacion/extractor.patch) y el
[extractor completo optimizado](../output/optimizacion/extractor-optimizado.zip)
para transferirlos al repositorio de su autor, sin publicar los PDFs.

Para repetir la medición aislada, detener primero los extractores y el balanceador
del proyecto principal: `docker compose stop extractor-lb extractor`, desde la
raíz. Así quedan libres el puerto 8080 y los recursos de las cinco réplicas. Copiar
los PDFs a `.test-extractor/tests/stress/pdfs/`. Desde `.test-extractor`:

```powershell
docker compose -p carga-local up --build -d
docker compose -p carga-local run --rm --service-ports -e K6_WEB_DASHBOARD=false -e K6_WEB_DASHBOARD_EXPORT=/stress/results/optimizado-k6.html k6 run --out web-dashboard --summary-export=/stress/results/optimizado-k6.json /stress/profesor/spike_tests.js
docker compose -p carga-local run --rm --entrypoint sh vegeta /stress/profesor/run.sh
```

Ejecutar una prueba a la vez y conservar cada carpeta de resultados antes de
repetirlas. Al terminar, detener ese entorno con `docker compose -p carga-local stop`
y volver a la raíz para ejecutar `docker compose up -d`. No mantener ambos grupos
de extractores activos durante una medición. El Compose del extractor contiene el comando de Uvicorn de 60 s;
usar solamente su Dockerfile no reproduce ese ajuste. Las dos corridas finales
permiten observar repetibilidad en esta PC, pero no eliminan la variación por
hardware, temperatura y procesos del host.

## Integración del proyecto

Documents-service ahora envía el PDF crudo por HTTP a `http://extractor-lb/extract`
con un cliente reutilizable. Conserva checksum y metadatos; la lectura de estos
últimos corre fuera del event loop. El índice único de checksum es obligatorio
al iniciar, la API lee como máximo 10 MiB + 1 byte antes de hashear y se evitaron
consultas que transferían el texto completo de MongoDB innecesariamente. El
frontend admite PDFs con MIME genérico y el despliegue utiliza `uv.lock`.

Validación: la suite completa de 68 tests de documents-service y 27 del extractor
pasó. Después se agregó el rechazo de `page_count=0` y pasaron los seis casos
parametrizados de esa validación; documents-service tiene ahora 69 casos. Se verificó
también la integración HTTP real: extracción 200, subida y guardado 201,
duplicado 409, PDF inválido 422, consulta y eliminación 200. Se utilizó una base
separada para esa prueba y se eliminó el documento creado. API, MongoDB, nginx y
las cinco réplicas quedaron funcionando con sus límites de recursos.
