"""
Stub del extractor-service para probar la infraestructura de carga.

Respeta la forma del contrato (POST /extract con el PDF crudo en el body,
GET /health) pero no procesa el PDF: sirve para validar balanceo, límites y
scripts antes de que exista el servicio real. Se elimina cuando extractor/
esté listo.
"""
from fastapi import FastAPI, Request

app = FastAPI(title="extractor-stub")


@app.post("/extract")
async def extract(request: Request) -> dict:
    await request.body()
    return {"content": "", "page_count": 1}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
