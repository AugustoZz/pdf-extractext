# Pruebas de carga y estrés

Scripts para medir el extractor-service con los perfiles de la cátedra.
Todo corre en Docker: no hace falta instalar k6 ni Vegeta.

```
tests/stress/
├── pdfs/      los 4 PDFs oficiales de la cátedra
├── k6/        prueba spike, modelo cerrado
├── vegeta/    prueba de carga fija, modelo abierto
├── stub/      extractor falso para probar la infraestructura
└── results/   salida de cada corrida (ignorada por git)
```

Igual que los scripts del profesor, el PDF va crudo en el body con
`Content-Type: application/pdf`. Desde el host, el extractor responde en
`http://localhost:8080/extract` (el puerto se cambia con `EXTRACTOR_PORT`).

## Cómo correrlas

Desde la raíz del repo, con el sistema levantado (`docker compose up --build -d`):

```bash
docker compose run --rm --service-ports k6
docker compose run --rm vegeta
```

| Prueba | Perfil | Resultados en `results/` |
|---|---|---|
| k6 (spike) | 0 → 100 VUs en 10 s, 20 s sostenidos, bajada a 0 en 10 s | `k6-spike.json`, `k6-spike.html` |
| Vegeta (carga fija) | 50 req/s durante 30 s, timeout 30 s | `vegeta-report.json`, `vegeta-plot.html` |

Mientras corre k6, el dashboard en vivo está en http://localhost:5665.

Vegeta acepta `RATE`, `DURATION` y `TIMEOUT` como variables de entorno,
por ejemplo `docker compose run --rm -e RATE=25 vegeta`. Para cambiar la cantidad de
réplicas del extractor: `EXTRACTOR_REPLICAS=1 docker compose up -d`.

## Probar sin el extractor real

Mientras `extractor/` no exista, el stub ocupa su lugar:

```bash
docker compose -f docker-compose.yml -f tests/stress/stub/compose.stub.yml up --build -d
```

Las pruebas se corren con los mismos comandos de arriba, agregando los dos `-f`.
