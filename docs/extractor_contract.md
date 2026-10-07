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
| Sin firma %PDF                   |  ???   | {"detail": …}  |
| PDF corrupto                     |  ???   | {"detail": …}  |
| Supera el tamaño máximo          |  ???   | {"detail": …}  |
| Falta el campo `file`            |  ???   | (lo genera FastAPI) |

## GET /health
200 {"status": "ok"}