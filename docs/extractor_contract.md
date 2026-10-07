# Contrato: extractor-service

## POST /extract

### Request
- Content-Type: multipart/form-data
- Campo `file`: el PDF (bytes)

### Respuesta exitosa: 200
{
  "text": "...",
  "page_count": ?,
  "metadata": { ... }
}

### Errores
| Situación                        | Código | Cuerpo         |
|----------------------------------|--------|----------------|
| Sin firma %PDF                   |  422   | {"detail": …}  |
| PDF corrupto                     |  422   | {"detail": …}  |
| Supera el tamaño máximo          |  422   | {"detail": …}  |
| Falta el campo `file`            |  422   | (lo genera FastAPI) |

## GET /health
200 {"status": "ok"}