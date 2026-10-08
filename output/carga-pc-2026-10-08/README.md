# Pruebas en PC de Augusto — 08/10/2026

Extractor commit: 236829facd728b0216f421f2598e0c9d3598fbd8
CPU: Intel Core i5-10400F. Docker: 12 CPUs lógicas, 8281104384 bytes RAM.
5 réplicas: 1 CPU / 1 GB cada una. nginx: 1 CPU / 512 MB.
PDFs oficiales verificados por SHA-256. API y MongoDB ociosos; réplicas duplicadas detenidas.

Tests: documentos 47 passed; extractor 21 passed.

| Métrica | Profesor | Esta PC |
|---|---:|---:|
| k6 req/s | 25,35 | 34,46 |
| k6 solicitudes | 1037 | 1381 |
| k6 errores | 0 % | 0 % |
| k6 p50 | 1,88 s | 2,45 s |
| k6 p95 | 8,80 s | 3,20 s |
| Vegeta throughput | 16,65 req/s | 9,80 req/s |
| Vegeta éxito | 66,53 % | 33,33 % |
| Vegeta p50 | 14,89 s | 20,002 s |

Vegeta: 500 HTTP 200; 973 HTTP 503; 27 código 0 (errores de transporte y timeout).
Una corrida por herramienta: k6 supera throughput de referencia, Vegeta no supera éxito ni latencia. Hardware distinto: esto no demuestra ventaja en igualdad de hardware.

Comandos:
- docker compose exec -T -e MONGODB_TEST_DB_NAME=pdf_extractext_test api pytest -q tests
- docker compose -p carga-local -f .test-extractor/docker-compose.yml run --rm --service-ports k6
- docker compose -p carga-local -f .test-extractor/docker-compose.yml run --rm vegeta
