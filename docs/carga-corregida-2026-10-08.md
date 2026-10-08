# Corridas con condiciones corregidas — 08/10/2026

> Este informe conserva las dos corridas por el gateway Windows de Docker Desktop.
> Las [dos corridas posteriores por los puertos del host Linux](carga-host-linux-2026-10-08.md)
> dieron 37,67–38,17 req/s en k6 y 100 % de éxito en Vegeta con TLS y límites activos.

Se ejecutaron dos parejas secuenciales de k6 y Vegeta con los cuatro PDFs
oficiales, HTTPS validado para k6, puertos publicados del host y límites Docker
explícitos para los generadores. **Estas corridas no superan al profesor.** Los
35 req/s y el 100 % de éxito anteriores corresponden a otro entorno: HTTP interno.

## Condiciones verificadas

| Componente | CPU máxima | RAM máxima |
|---|---:|---:|
| Cada extractor, cinco réplicas | 1 | 1 GiB |
| nginx | 1 | 512 MiB |
| k6 | 2 | 3 GiB |
| Vegeta | 1 | 1 GiB |

La memoria de k6 contempla los PDFs que abre cada VU del script original;
se observaron aproximadamente 2,07 GiB durante la primera corrida.
`GOMEMLIMIT=1GiB` se mantuvo como ajuste del recolector, independiente del límite
Docker. Se registraron los límites efectivos con `docker inspect`.

k6 mantuvo `https://extract.universidad.localhost/extract`, resolviendo ese nombre
al gateway del host dentro del contenedor. nginx publicó 443 y el probe confirmó
TLS 1.3, HTTP/1.1 y validación mediante una CA local. No se omitió la verificación
TLS ni se cambió el almacén de certificados de Windows. Vegeta accedió al puerto
publicado con `http://host.docker.internal:8080/extract`; `localhost` dentro del
generador apuntaría al propio contenedor.

k6: 10 s hasta 100 VUs, 20 s sostenidos y 10 s hasta 0. Vegeta: 50 solicitudes/s
durante 30 s, rotando cuatro PDFs y con timeout de cliente de 30 s. Se verificaron
los SHA-256 oficiales. No hubo generadores simultáneos ni dos grupos activos de
extractores. El algoritmo no cambió y cada solicitud volvió a extraerse.

## Resultados

| Métrica | Corrida 1 | Corrida 2 | Profesor |
|---|---:|---:|---:|
| k6 solicitudes | 510 | 590 | 1.037 |
| k6 solicitudes/s | 11,80492 | 13,80418 | 25,35 |
| k6 errores | 0 % | 0 % | 0 % |
| k6 mediana | 3,097 s | 2,294 s | 1,88 s |
| k6 p95 | 19,862 s | 19,463 s | 8,80 s |
| Vegeta solicitudes | 1.500 | 1.500 | 1.500 |
| Vegeta tasa de envío | 50,03276/s | 50,03368/s | 50/s |
| Vegeta throughput efectivo | 7,18116/s | 7,59244/s | 16,65/s |
| Vegeta éxito | 28,47 % | 29,27 % | 66,53 % |
| Vegeta mediana | 22,195 s | 22,023 s | 14,89 s |
| Vegeta p95 | 30,001 s | 30,001 s | — |

Vegeta 1: 427 respuestas 200, 721 respuestas 503 y 352 errores con código 0.
Vegeta 2: 439 respuestas 200, 714 respuestas 503 y 347 errores con código 0.
Código 0 incluye transporte y timeout; no se clasifica todo como timeout.
El comando terminó y generó los reportes, pero hubo fallos bajo carga.

## Interpretación y límites

El envío medio del PDF en k6 fue de 4,850 y 3,848 s; la espera media de respuesta
fue de 1,686 y 1,665 s. En la corrida HTTP interna anterior el envío medio era
aproximadamente 0,004 s. La transferencia representa ahora una parte importante
de la latencia. Se cambiaron conjuntamente red, TLS y límites del generador;
estos datos no permiten atribuir toda la diferencia a una sola causa.

El entorno es Docker Desktop/WSL2 en esta PC: no reproduce el hardware ni toda
la configuración TLS/red del profesor. Se corrigieron las salvedades de ejecución
identificadas, pero las métricas actuales no demuestran el rendimiento para el
extra. No se aumentó el timeout ni se agregó caché de resultados.

## Evidencia

- [Resumen derivado de los JSON](../output/carga-corregida-2026-10-08/resumen.json).
- Corrida 1: [k6 JSON](../output/carga-corregida-2026-10-08/corrida-1/corregido-k6.json),
  [dashboard](../output/carga-corregida-2026-10-08/corrida-1/corregido-k6.html),
  [Vegeta JSON](../output/carga-corregida-2026-10-08/corrida-1/profesor-vegeta.json) y
  [gráfico](../output/carga-corregida-2026-10-08/corrida-1/profesor-vegeta.html).
- Corrida 2: [k6 JSON](../output/carga-corregida-2026-10-08/corrida-2/corregido-k6.json),
  [dashboard](../output/carga-corregida-2026-10-08/corrida-2/corregido-k6.html),
  [Vegeta JSON](../output/carga-corregida-2026-10-08/corrida-2/profesor-vegeta.json) y
  [gráfico](../output/carga-corregida-2026-10-08/corrida-2/profesor-vegeta.html).

Ver `tests/stress/profesor/README.md` del extractor para reproducir. Los
certificados se generan localmente, duran siete días y se excluyen de Git.
Los binarios de Vegeta quedan locales y no se versionan. Al terminar se detuvo
el entorno de carga y se restauró el proyecto principal.
