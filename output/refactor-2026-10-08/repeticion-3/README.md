# Nueva corrida — 8 de octubre de 2026, 18:41 ART

Se ejecutaron k6 y Vegeta secuencialmente sobre la versión refactorizada, sin
modificar código ni perfiles. La verificación previa de HTTPS y contrato de
los cuatro PDFs oficiales pasó.

| Métrica | k6 | Vegeta |
|---|---:|---:|
| Solicitudes | 1.505 | 1.500 |
| Rendimiento efectivo | 37,54 req/s | 33,15 req/s |
| HTTP 200 | 100 % | 100 % |
| Errores/timeouts | 0 | 0 |
| Mediana | 2,37 s | 7,44 s |
| p95 | 2,88 s | 16,19 s |

k6 mantuvo las etapas 10/20/10 s hasta 100 usuarios. Vegeta generó 50,03 req/s
durante 29,98 s, con timeout de cliente de 30 s; la espera posterior fue 15,26 s.
Su rendimiento efectivo incluye esa espera.

Se verificaron cinco extractores activos con límites de 1 CPU/1 GiB cada uno.
Los generadores finalizaron con código 0, sin OOM: k6 con 2 CPU/3 GiB y Vegeta
con 1 CPU/1 GiB. nginx mantuvo su configuración de 1 CPU/512 MiB.
Se usaron los puertos publicados del host Linux de Docker Desktop: HTTPS para
k6, con certificado validado, y HTTP/8080 para Vegeta.

Comparación con el profesor: k6 supera 25,35 req/s; Vegeta supera 16,65 req/s
efectivos y 66,53 % de éxito, y mejora su mediana de 14,89 s. La mediana de k6
sigue por encima de 1,88 s. Son equipos distintos; el puntaje depende de la cátedra.

Respecto de la corrida anterior de la versión refactorizada, k6 subió de 36,67
a 37,54 req/s, pero Vegeta bajó de 36,43 a 33,15 req/s y su p95 aumentó de 9,74
a 16,19 s. Se conserva esta variación; no se determinó su causa.

Evidencia: [resumen](summary.json), [JSON k6](corregido-k6.json),
[dashboard k6](corregido-k6.html), [JSON Vegeta](profesor-vegeta.json),
[gráfico Vegeta](profesor-vegeta.html), [servicios y límites](services.json).

El proyecto principal quedó restaurado. Health en 8080 y frontend en 8000
devolvieron HTTP 200.
