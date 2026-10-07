# Contrato: extractor-service

## POST /extract

### Request
- Content-Type: multipart/form-data
- Campo `file`: el PDF (bytes)

### Respuesta exitosa: 200
{
  "text": "Texto extraído exitosamente",
  "page_count": int,
  "metadata": { ... }
}

- `text`: puede ser "" (PDF escaneado sin texto seleccionable)
- `page_count`: entero, mayor o igual a 1
- `metadata`: objeto; claves en minúsculas; puede ser {}


## Validaciones
- El extractor valida el contenido: tamaño, firma %PDF e integridad
- La extensión .pdf y el content-type los valida quen llama
- Los PDFs con restricciones pero sin clave de apertura se aceptan

| Situación                        | Código | Cuerpo                                            |
|----------------------------------|--------|-------------------------------------------------  |
| Sin firma %PDF                   |  422   | {"detail": "El archivo no tiene firma PDF..."}     |
| PDF corrupto                     |  422   | {"detail": "El archivo PDF está corrupto..."}      |
| Supera el tamaño máximo          |  413   | {"detail": "El archivo supera el tamaño..."}       |
| Falta el campo `file`            |  422   | (lo genera FastAPI)                                |
| PDF protegido con contraseña     |  422   | {"detail": "mensaje en texto}  |

## To-do
- Resolver conflictos de tamaño máximo del file, decidir quien valida el tamaño de archivo

## GET /health
200 {"status": "ok"}