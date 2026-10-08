# Evidencia de las pruebas corregidas

Las [pruebas finales por los puertos del host Linux](../../docs/carga-host-linux-2026-10-08.md)
están en `host-linux-1/` y `host-linux-2/`: k6 37,67–38,17 req/s sin errores,
Vegeta 34,64–34,67 req/s efectivos y 100 % de éxito. `resumen-host-linux.json`
se deriva directamente de sus JSON. Se conserva también la publicación real
de puertos y los límites/resolución de los generadores.

Ver el [informe actualizado](../../docs/carga-corregida-2026-10-08.md).
Se ejecutaron dos parejas de k6 y Vegeta con HTTPS/puertos publicados y límites
Docker de generadores. Cada carpeta conserva JSON y HTML de ambas herramientas,
y el binario original de Vegeta permanece local, excluido de Git.
`resumen.json` se calculó directamente desde esos JSON. La configuración del
entorno está en `output/optimizacion/configuracion-corregida.json`.

No se superó al profesor con estas condiciones: k6 11,80–13,80 req/s y Vegeta
28,47–29,27 % de éxito. Las mediciones de HTTP interno son otro entorno.
