# Repetición con scripts del profesor — 08/10/2026

Se usó spike_tests.js original: solo cambió BASE_URL y rutas a PDFs.
Se usó test_carga.txt original: solo cambió host y rutas. UTF-8 sin BOM.
Vegeta: comandos originales; RATE=50, DURATION=30s; timeout por defecto 30s.
Mismo hardware y límites que la corrida adaptada; cinco réplicas.
GOMEMLIMIT=1GiB del Compose se mantuvo.

| Métrica | Profesor | Esta PC |
|---|---:|---:|
| k6 req/s | 25,35 | 31,91 |
| k6 solicitudes | 1037 | 1281 |
| k6 errores | 0 % | 0 % |
| k6 p50 | 1,88 s | 2,764 s |
| k6 p95 | 8,80 s | 3,546 s |
| Vegeta throughput | 16,65 req/s | 7,36 req/s |
| Vegeta éxito | 66,53 % | 29,40 % |
| Vegeta p50 | 14,89 s | 26,826 s |

Vegeta: 441 HTTP 200, 433 HTTP 503, 40 HTTP 502 y 586 código 0.
Código 0 comprende errores de transporte y timeout.
No se alcanzan las condiciones completas del puntaje extra. Una corrida en hardware distinto.

k6 produjo advertencia de dashboard duplicado por combinar variable de entorno y --out web-dashboard; sí generó HTML y JSON.
