# Informe: Test de carga, estrés y optimización del extractor-service

## 1. Arquitectura

```
cliente (k6 / Vegeta) ──► extractor-lb (nginx, least_conn) ──► extractor × 5 réplicas
```

- **extractor-lb:** reparte las peticiones con `least_conn`, porque el tiempo de
  procesamiento varía mucho según el PDF.
- **extractor:** _(completar: librería, modelo de workers, control de concurrencia)_

Decisiones de diseño: _(completar a medida que se toman, con su justificación)_

## 2. Entorno de medición

| | |
|---|---|
| Host | _(CPU, núcleos, RAM, sistema operativo)_ |
| Docker | _(versión)_ |
| Límites por réplica | 1.0 CPU, 1 GB RAM |
| Réplicas | 5 |
| PDFs | `tests/stress/pdfs` (set oficial de la cátedra) |

Los generadores de carga corren en el mismo host y compiten por CPU con el servicio.

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
- **Pendiente:** k6 usa ~3,5 GB de RAM (cada VU guarda su copia de los PDFs) y compite con
  las réplicas por la memoria del host.

### Experimento N: _(título)_

- **Hipótesis:**
- **Cambio:**
- **Resultado:** _(métricas antes / después)_
- **Conclusión:** _(se mantiene o se descarta, y por qué)_

## 5. Cuello de botella y conclusiones

_(completar)_
