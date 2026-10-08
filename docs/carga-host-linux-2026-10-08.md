# Pruebas finales: TLS y puertos publicados del host Linux — 08/10/2026

Dos corridas consecutivas conservaron HTTPS validado, puertos publicados del host,
límites de todos los contenedores y los perfiles del profesor. Resultado:
**k6 37,67–38,17 req/s sin errores; Vegeta 34,64–34,67 req/s efectivos y 100 % de
éxito (1.500/1.500 por corrida)**. Superan los valores publicados de throughput,
éxito y mediana de Vegeta. La mediana de k6 del profesor sigue siendo menor.

## Ruta medida y condiciones

Docker Desktop ofrece una ruta hacia Windows mediante `host-gateway` y otra hacia
su host Linux virtual en WSL2. Las primeras dos pruebas usaron el gateway Windows
y dieron malos resultados; están conservadas en el
[informe de esa ruta](carga-corregida-2026-10-08.md).

Las últimas dos usaron el gateway del host Linux. El nombre de k6 siguió siendo
`extract.universidad.localhost`, con HTTPS en 443; Vegeta siguió accediendo al
puerto publicado 8080 mediante `host.docker.internal`. `LOAD_HOST_GATEWAY` controla
la resolución dentro de los generadores. Se consulta la IP al arrancar.

En estas corridas, el gateway era `172.19.0.1` y nginx tenía `172.19.0.7`.
El Docker host publicó 443 hacia nginx:443 y 8080 hacia nginx:80, como confirma
[la configuración real de red y puertos](../output/carga-corregida-2026-10-08/host-linux-2/nginx-red-puertos.json).
Las solicitudes entraron por los puertos del host Linux. El probe confirmó TLS 1.3,
HTTP/1.1 y respuestas correctas para los cuatro PDFs, usando una CA local validada.

| Componente | CPU máxima | RAM máxima |
|---|---:|---:|
| Cada extractor, cinco réplicas | 1 | 1 GiB |
| nginx | 1 | 512 MiB |
| k6 | 2 | 3 GiB |
| Vegeta | 1 | 1 GiB |

Los límites de los generadores y la resolución de nombres se conservaron en
sus `*-hostconfig.json`. Ambos terminaron con código 0 y `OOM=false` en las dos
corridas. k6 mantuvo `GOMEMLIMIT=1GiB`; su límite Docker de 3 GiB contempla los PDFs
abiertos por los 100 VUs del script original.

k6 conservó las etapas 10/20/10 s y 100 VUs. Vegeta conservó 50 solicitudes/s
durante 30 s y timeout de 30 s. Se verificaron los mismos cuatro SHA-256 oficiales.
Los generadores se ejecutaron secuencialmente y sólo hubo cinco extractores activos.
Se mantuvieron el algoritmo, los límites de la aplicación y la extracción por
petición; el cambio entre las rutas Windows y Linux fue la resolución del host.

## Resultados verificados

| Métrica | Linux 1 | Linux 2 | Referencia del profesor |
|---|---:|---:|---:|
| k6 solicitudes | 1.529 | 1.508 | 1.037 |
| k6 throughput | 38,16805/s | 37,66513/s | 25,35/s |
| k6 errores | 0 % | 0 % | 0 % |
| k6 mediana | 2,324 s | 2,329 s | 1,88 s |
| k6 p95 | 2,866 s | 2,980 s | 8,80 s |
| Vegeta solicitudes | 1.500 | 1.500 | 1.500 |
| Vegeta tasa de envío | 50,03242/s | 50,03333/s | 50/s |
| Vegeta throughput efectivo | 34,64151/s | 34,66997/s | 16,65/s |
| Vegeta éxito | 100 % | 100 % | 66,53 % |
| Vegeta mediana | 6,643 s | 6,576 s | 14,89 s |
| Vegeta p95 | 12,240 s | 11,578 s | — |
| Vegeta máximo | 18,267 s | 18,803 s | — |

En ambas corridas hubo 1.500 respuestas 200 de Vegeta, sin 503, errores de
transporte ni timeout. El throughput efectivo incluye la espera posterior al
ataque; no se confundió con la tasa de envío de 50/s.

El envío medio del PDF en k6 cayó de 3,85–4,85 s por el gateway Windows a
6,57–6,68 ms por el host Linux. Esta comparación mantiene TLS y límites del
generador, y muestra el impacto del recorrido adicional de Docker Desktop hacia
Windows. No se deben mezclar estas mediciones con las de HTTP interno o Windows.

Se cumplen las mejoras numéricas solicitadas para superar la referencia:
throughput mayor en k6, mejor éxito y mediana en Vegeta. El profesor debe validar
la comparación: su hardware, certificados y configuración completa no se
reproducen exactamente; el primer puesto depende de las demás entregas.

## Evidencia y reproducción

- [Resumen derivado de los JSON](../output/carga-corregida-2026-10-08/resumen-host-linux.json).
- Linux 1: [k6](../output/carga-corregida-2026-10-08/host-linux-1/corregido-k6.json),
  [dashboard](../output/carga-corregida-2026-10-08/host-linux-1/corregido-k6.html),
  [Vegeta](../output/carga-corregida-2026-10-08/host-linux-1/profesor-vegeta.json),
  [gráfico](../output/carga-corregida-2026-10-08/host-linux-1/profesor-vegeta.html).
- Linux 2: [k6](../output/carga-corregida-2026-10-08/host-linux-2/corregido-k6.json),
  [dashboard](../output/carga-corregida-2026-10-08/host-linux-2/corregido-k6.html),
  [Vegeta](../output/carga-corregida-2026-10-08/host-linux-2/profesor-vegeta.json),
  [gráfico](../output/carga-corregida-2026-10-08/host-linux-2/profesor-vegeta.html).

El README `tests/stress/profesor/README.md` del extractor incluye los comandos
con TLS y consulta dinámica del gateway Linux. Omitir `LOAD_HOST_GATEWAY` reproduce
la ruta Windows en Docker Desktop. Al terminar se restauró el proyecto principal;
los cambios y resultados siguen locales y deben publicarse para la entrega.

## Nueva repetición del 8 de octubre

Se repitieron los mismos perfiles y límites sin modificar el código. k6 obtuvo 31,09 solicitudes/s, 1.246 respuestas HTTP 200 y cero errores. Vegeta obtuvo 26,67 solicitudes/s efectivas, 1.465 respuestas HTTP 200 de 1.500 (97,67 %) y 35 timeouts; mediana de 11,94 s y p95 de 27,17 s.

Esta corrida muestra variación respecto de las dos anteriores: el 100 % de éxito de Vegeta no se mantuvo. No se midió la causa de la variación. La comparación con el profesor sigue siendo entre equipos diferentes.

[Condiciones, resultados y evidencia de la nueva repetición](../output/carga-corregida-2026-10-08/repeticion-pdf-3/README.md).