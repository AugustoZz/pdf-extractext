# 📄 pdf-extractext

> Aplicación web para extracción de texto desde archivos PDF, con persistencia en base de datos no relacional y gestión CRUD de documentos. Inspirado en ILovePDF.

**Universidad Tecnológica Nacional — Facultad Regional San Rafael**
**Ingeniería en Sistemas | Desarrollo de Software 2026**

**Integrantes: Mansalve Augusto, Praderio Valentín, Quiroga Constanza**

---

## Descripción

`pdf-extractext` permite a los usuarios enviar archivos PDF y obtener el texto extraído. El sistema valida el archivo, genera un checksum para evitar duplicados y persiste el contenido en una base de datos no relacional (MongoDB). Expone una API REST construida con FastAPI.

---

## Tecnologías

| Tecnología | Uso |
|---|---|
| **Python 3.11+** | Lenguaje principal |
| **FastAPI** | Framework web / API REST |
| **uv** | Gestor de paquetes y entornos virtuales |
| **MongoDB** | Base de datos no relacional (driver asíncrono `motor`) |
| **pypdf** | Extracción de texto y metadatos desde PDFs |
| **pytest** | Testing (TDD) |

---

## Arquitectura del Proyecto

```
pdf-extractext/
│
├── app/                        # Código fuente principal
│   ├── main.py                 # Punto de entrada de la aplicación
│   ├── api/                    # Capa de presentación (rutas HTTP)
│   │   └── v1/
│   │       └── endpoints/      # Endpoints REST organizados por recurso
│   ├── core/                   # Núcleo de la aplicación
│   │   └── config/             # Configuración (12-Factor: variables de entorno)
│   ├── infrastructure/         # Capa de infraestructura
│   │   └── database/           # Conexión y operaciones MongoDB
│   └── services/               # Lógica de negocio
│       └── extractor/          # Servicio de extracción de texto PDF
│
├── frontend/                   # Cliente web estático (servido en /web)
│
├── tests/                      # Suite de pruebas (TDD)
│   ├── unit/                   # Pruebas unitarias
│   └── integration/            # Pruebas de integración
│
├── docs/                       # Documentación del proyecto
├── .env.example                # Variables de entorno requeridas (12-Factor)
├── requirements.txt            # Dependencias del proyecto
├── Dockerfile                  # Imagen de la aplicación
├── docker-compose.yml          # Orquestación API + MongoDB
└── README.md
```
---

## Instalación y Ejecución

### Requisitos previos
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) instalado
- MongoDB en ejecución (o usar la Opción 2 con Docker)

### Pasos (Opción 1: Local con uv)

```bash
# 1. Clonar el repositorio
git clone https://github.com/AugustoZz/pdf-extractext.git
cd pdf-extractext

# 2. Crear entorno virtual e instalar dependencias
uv venv
uv pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env

# 4. Ejecutar la aplicación
uv run python main.py
```

La API estará disponible en `http://localhost:8000`
Documentación interactiva en `http://localhost:8000/docs`

### Pasos (Opción 2: Usando Docker - ¡Recomendado!)

Para evaluar el proyecto sin instalar Python o MongoDB localmente:

```bash
# 1. Clonar el repositorio
git clone https://github.com/AugustoZz/pdf-extractext.git
cd pdf-extractext

# 2. Levantar la base de datos y la API
docker compose up --build
```
La API estará lista y conectada a la base de datos automáticamente en `http://localhost:8000`.

---

## Testing (TDD)

Este proyecto aplica **Test Driven Development**. Las pruebas se ejecutan con:

```bash
uv run pytest
```

```bash
# Solo pruebas unitarias (no requieren MongoDB)
uv run pytest tests/unit/

# Solo pruebas de integración (requieren MongoDB levantado)
uv run pytest tests/integration/

# Con cobertura
uv run pytest --cov=app
```

> **Base de datos de test.** Las pruebas de integración borran la colección
> `documents` antes y después de cada test. Por eso se conectan a una base
> **separada**, definida en `MONGODB_TEST_DB_NAME` (por defecto
> `pdf_extractext_test`), y verifican que sea distinta de `MONGODB_DB_NAME`
> antes de tocar nada.

---

## Endpoints de la API

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/v1/extract` | Subir un PDF, extraer su texto y persistirlo |
| `GET` | `/api/v1/documents` | Listar documentos (paginado con `skip` y `limit`) |
| `GET` | `/api/v1/documents/{id}` | Obtener documento por ID |
| `PUT` | `/api/v1/documents/{id}` | Actualizar documento (`filename`, `text`, `metadata`) |
| `DELETE` | `/api/v1/documents/{id}` | Eliminar documento |

Códigos de respuesta relevantes de `POST /api/v1/extract`:

| Código | Significado |
|--------|-------------|
| `201` | Documento extraído y guardado |
| `400` | El archivo no tiene extensión `.pdf` |
| `409` | Ya existe un documento con el mismo checksum |
| `422` | El PDF es inválido, está corrupto o supera `MAX_FILE_SIZE_MB` |

---

## Principios Aplicados

- **12-Factor App** — Configuración por variables de entorno, dependencias explícitas, procesos sin estado
- **TDD** — Test Driven Development con pytest
- **SOLID** — Principios de diseño orientado a objetos
- **DRY** — Don't Repeat Yourself
- **KISS** — Keep It Simple, Stupid
- **YAGNI** — You Aren't Gonna Need It
- **Clean Architecture** — Separación de capas (API → Services → Infrastructure)

---

## Los 12 Factores

| Factor | Implementación |
|--------|----------------|
| **I. Codebase** | Un repositorio Git, múltiples deploys |
| **II. Dependencies** | `requirements.txt` + `uv` — dependencias declaradas explícitamente |
| **III. Config** | Variables de entorno vía `.env` (nunca en código) |
| **IV. Backing Services** | MongoDB como recurso adjunto configurable |
| **V. Build/Release/Run** | Separación clara usando Docker y Docker Compose |
| **VI. Processes** | La app es stateless — no guarda estado entre requests |
| **VII. Port Binding** | FastAPI expone el servicio vía puerto configurable |
| **VIII. Concurrency** | Escalable horizontalmente con workers uvicorn |
| **IX. Disposability** | Arranque rápido, cierre limpio |
| **X. Dev/Prod Parity** | Mismo stack en dev y prod |
| **XI. Logs** | Tratados como streams de eventos (stdout) |
| **XII. Admin Processes** | Tareas de gestión como procesos independientes |

---

## Plazo de Entrega

**23/05/2025** — Etapa N°1

---

## Licencia

MIT © 2026 — Universidad Tecnológica Nacional