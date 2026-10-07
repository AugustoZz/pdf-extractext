# Contrato: extractor-service

Servicio sin estado que recibe un PDF y devuelve su texto en Markdown. Es el
microservicio que evalúa el TP de carga, así que la entrada y la salida siguen
lo que piden la consigna y los scripts de prueba del profesor.

## POST /extract

### Request
- Body: los bytes del PDF, sin multipart.
- Header: `Content-Type: application/pdf`.

Es el formato que envían los scripts de k6 y Vegeta de la cátedra.

### Respuesta exitosa: 200
```json
{
  "content": "# Título\n\nTexto del documento...",
  "page_count": 12
}
```

- `content`: texto del PDF en formato Markdown. Puede ser `""` si el PDF no tiene
  texto seleccionable (por ejemplo, un PDF escaneado sin OCR).
- `page_count`: entero, mayor o igual a 1.

### Errores
| Situación                         | Código | Cuerpo                                         |
|-----------------------------------|--------|------------------------------------------------|
| Body vacío o sin firma `%PDF`     |  422   | `{"detail": "El archivo no tiene firma PDF..."}` |
| PDF corrupto                      |  422   | `{"detail": "El archivo PDF está corrupto..."}`  |
| PDF protegido con contraseña      |  422   | `{"detail": "El archivo PDF está protegido..."}` |
| Supera el tamaño máximo           |  413   | `{"detail": "El archivo supera el tamaño..."}`   |
| Servicio saturado (backpressure)  |  503   | `{"detail": "Servicio saturado, reintentar."}`   |

El 503 se responde de inmediato cuando el servicio no puede procesar la petición
a tiempo, en vez de encolarla hasta que el cliente corte por timeout.

## GET /health
200 `{"status": "ok"}`

## Validaciones
- El extractor valida el contenido: tamaño, firma `%PDF`, integridad y que no
  requiera contraseña de apertura. Los PDFs con restricciones de propietario pero
  sin clave de apertura se aceptan.
- La extensión `.pdf` y el content-type los valida quien llama (documents-service).

## Ejecución
- Escucha en el puerto **8000** dentro del contenedor.
- La imagen incluye Python: el healthcheck de `docker-compose.yml` llama a `/health`
  con `python -c`.
- Configuración por variables de entorno (por ejemplo, `MAX_FILE_SIZE_MB`, por
  defecto 10) y logs a stdout.
- Sin estado: cualquier réplica puede atender cualquier petición.
