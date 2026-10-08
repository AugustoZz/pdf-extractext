# Repetición de carga — 8 de octubre de 2026

Corrida nueva, sin cambios de código entre las mediciones anteriores y esta repetición. Se conservaron los resultados anteriores.

## Condiciones

- Cuatro PDFs oficiales, enviados crudos con `Content-Type: application/pdf`.
- k6: script del profesor con rutas de archivos adaptadas; 10 s hasta 100 usuarios, 20 s a 100 usuarios, 10 s de descenso. HTTPS con certificado validado.
- Vegeta: 50 solicitudes/s durante 30 s, 1.500 solicitudes, cuatro PDFs en rotación y timeout de 30 s.
- Cinco extractores, cada uno limitado a 1 CPU y 1 GiB; nginx a 1 CPU y 512 MiB.
- Generadores limitados: k6 a 2 CPU y 3 GiB; Vegeta a 1 CPU y 1 GiB. El límite mayor de k6 permite cargar los cuatro archivos en cada usuario virtual.
- Generadores en Docker, usando los puertos publicados 443 y 8080 del host Linux de Docker Desktop, mediante 172.19.0.1. Esto evita el reenviador adicional de Windows. No se utilizó la IP directa del extractor.
- Se detuvieron los extractores del proyecto principal durante la medición para mantener cinco réplicas activas. No hubo terminaciones por falta de memoria.

## Resultados

| Métrica | k6 | Vegeta |
|---|---:|---:|
| Solicitudes | 1.246 | 1.500 |
| Rendimiento efectivo | 31,09 solicitudes/s | 26,67 solicitudes/s |
| HTTP 200 | 100 % | 97,67 % (1.465) |
| Errores | 0 | 35 timeouts |
| Latencia mediana | 2,83 s | 11,94 s |
| Latencia p95 | 3,62 s | 27,17 s |

Vegeta generó tráfico a 50,03 solicitudes/s; su rendimiento efectivo incluye la espera de las respuestas. El ataque duró 29,98 s y la espera posterior 24,94 s.

Los resultados son inferiores a las dos corridas anteriores (k6: 37,67–38,17 solicitudes/s; Vegeta: 100 % de éxito). Esta repetición no permite afirmar que el éxito del 100 % sea estable. No se midió la causa de la variación.

Frente a la referencia registrada del profesor, k6 supera 25,35 solicitudes/s y Vegeta mejora el 66,53 % de éxito y la mediana de 14,89 s. La mediana de k6 es mayor que sus 1,88 s. La comparación entre equipos distintos no garantiza el puntaje extra.

## Evidencia

- [Resumen k6](corregido-k6.json) y [dashboard](corregido-k6.html).
- [Resumen Vegeta](profesor-vegeta.json), [gráfico](profesor-vegeta.html) y binario local `profesor-vegeta.bin`.
- [Límites y puertos de servicios](recursos-servicios.txt).
- [Estado final y límites de generadores](estados-generadores.txt), [configuración k6](k6-hostconfig.json) y [configuración Vegeta](vegeta-hostconfig.json).

Al finalizar se detuvo el entorno de carga y se restauró el proyecto principal. Tanto `/health` en el puerto 8080 como `/web/index.html` en el puerto 8000 devolvieron HTTP 200.
