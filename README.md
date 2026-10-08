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
| **httpx** | Cliente asíncrono con conexiones reutilizables al extractor |
| **pypdf** | Lectura opcional de metadatos; el texto se extrae en el microservicio externo |
| **pytest** | Testing (TDD) |

---

## Arquitectura del Proyecto

Esta rama utiliza el [extractor optimizado](https://github.com/AugustoZz/pdf-extractext-extractor/tree/perf/refactor-carga-2026-10-08),
fork del repositorio de valendotjpg. Docker Compose fija el commit
`3e825acbfd1c425f191d1bb5e94e21cd0642a156` para reproducir la versión probada.
Con `EXTRACTOR_BUILD_CONTEXT` se puede seleccionar otra copia del extractor.

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
│       └── extractor/          # Cliente HTTP del extractor y lectura de metadatos
│
├── frontend/                   # Cliente web estático (servido en /web)
│
├── tests/                      # Suite de pruebas (TDD)
│   ├── unit/                   # Pruebas unitarias
│   └── integration/            # Pruebas de integración
│
├── docs/                       # Documentación del proyecto
├── .env.example                # Variables de entorno requeridas (12-Factor)
├── pyproject.toml              # Dependencias y grupo de desarrollo para uv
├── uv.lock                     # Versiones exactas reproducibles
├── requirements.txt            # Export compatible generado desde uv.lock
├── Dockerfile                  # Imagen de la aplicación
├── docker-compose.yml          # Orquestación API + MongoDB + extractor
├── nginx/extractor.conf        # Balanceador HTTP hacia las cinco réplicas
└── README.md
```
---

## Instalación y Ejecución

### Requisitos previos
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) instalado
- MongoDB y extractor HTTP en ejecución (o usar la Opción 2 con Docker)

### Pasos (Opción 1: Local con uv)

```bash
# 1. Clonar el repositorio
git clone https://github.com/AugustoZz/pdf-extractext.git
cd pdf-extractext

# 2. Crear entorno virtual e instalar dependencias
uv sync --frozen

# 3. Configurar variables de entorno
cp .env.example .env
# Para ejecutar la API fuera de Docker, configurar EXTRACTOR_URL en .env
# con la URL publicada del extractor, por ejemplo http://localhost:8080/extract.

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

# 2. Levantar MongoDB, la API y las cinco réplicas del extractor
docker compose up --build
```
La API estará lista y conectada a la base de datos automáticamente en `http://localhost:8000`.
El extractor balanceado queda publicado en `http://localhost:8080/extract`.
Docker Compose inicia la API sin watcher de recarga para evitar consumir CPU
vigilando los PDFs y resultados; tras editar código, usar `docker compose restart api`.
Si algún puerto ya está en uso en tu máquina, cambialo en `.env` (ver la sección Docker Compose de `.env.example`).

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

También se puede ejecutar toda la suite desde Docker, sin Python en el host:

```bash
docker compose exec api uv run --frozen pytest
```

> **Base de datos de test.** Las pruebas de integración borran la colección
> `documents` antes y después de cada test. Por eso se conectan a una base
> **separada**, definida en `MONGODB_TEST_DB_NAME` (por defecto
> `pdf_extractext_test`), y verifican que sea distinta de `MONGODB_DB_NAME`
> antes de tocar nada.

---

## Microservicios

Cada microservicio vive en su propio repositorio:

| Servicio | Repositorio | Qué hace |
|---|---|---|
| **api** (documentos) | este repositorio | API REST, frontend y persistencia en MongoDB |
| **extractor** | [pdf-extractext-extractor](https://github.com/valendotjpg/pdf-extractext-extractor) | Recibe un PDF y devuelve su texto en Markdown |

`docker compose up --build` construye el extractor directamente desde su repositorio
(5 réplicas). Dentro de la red de Compose el balanceador responde en
`http://extractor-lb/extract` y distribuye cada solicitud con `least_conn`.

La API de documentos envía el PDF binario al extractor mediante `httpx.AsyncClient`
y reutiliza las conexiones. Guarda su `content` como `text` (Markdown), conserva
`page_count`, checksum y metadatos y evita repetir la extracción de texto con pypdf.
Los errores 422, 413 y 503 del extractor se propagan; los errores de conexión devuelven
503 y una respuesta externa inválida devuelve 502. No se persiste un documento si
falló la extracción.

`EXTRACTOR_URL` y `EXTRACTOR_TIMEOUT_SECONDS` permiten conectar otro despliegue
(por defecto `http://extractor-lb/extract`). Para probar una copia local optimizada
del servicio, configurar `EXTRACTOR_BUILD_CONTEXT=./.test-extractor` en `.env`;
por defecto se usa el repositorio remoto. La copia local debe existir antes del build.

El TP de **Test de Carga, Estrés y Optimización** se entrega en el repositorio del
extractor: ahí están las pruebas con k6 y Vegeta, el informe, la evidencia de la corrida
final y el contrato del servicio.

Las [pruebas previas](docs/carga-host-linux-2026-10-08.md), con HTTPS validado,
puertos publicados del host Linux y límites explícitos de generadores, dieron
37,67–38,17 solicitudes/s sin errores en k6 y 100 % de éxito en Vegeta.
La [refactorización posterior](docs/refactor-2026-10-08.md) documenta el control
de cancelaciones, la memoria compartida y una nueva comparación antes/después.
Los informes distinguen esta ruta de HTTP interno y del gateway Windows.
Se incluyen un parche y ZIP para el repositorio del extractor.

---

## Endpoints de la API

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/v1/extract` | Subir un PDF, extraer su texto y persistirlo |
| `GET` | `/api/v1/documents` | Listar documentos, del más reciente al más antiguo (paginado con `skip` y `limit`). **No incluye el campo `text`** |
| `GET` | `/api/v1/documents/{id}` | Obtener documento por ID |
| `PUT` | `/api/v1/documents/{id}` | Actualizar documento (`filename`, `text`, `metadata`) |
| `DELETE` | `/api/v1/documents/{id}` | Eliminar documento |

Códigos de respuesta relevantes de `POST /api/v1/extract`:

| Código | Significado |
|--------|-------------|
| `201` | Documento extraído y guardado |
| `400` | El archivo no tiene extensión `.pdf` |
| `409` | Ya existe un documento con el mismo checksum |
| `413` | El archivo supera `MAX_FILE_SIZE_MB` |
| `415` | El cliente declaró un MIME incompatible con PDF (se acepta MIME vacío o genérico) |
| `422` | El PDF es inválido, está corrupto o tiene contraseña |
| `503` | El extractor está saturado, no responde o no está disponible |
| `502` | El extractor devolvió una respuesta inesperada o inválida |

El índice único de checksum es obligatorio al arrancar. Si hay duplicados previos
o MongoDB no puede crearlo, la API falla al iniciar: corregir el problema e iniciar
nuevamente garantiza que las subidas concurrentes no generen duplicados.

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
| **II. Dependencies** | `pyproject.toml` + `uv.lock` + `uv sync --frozen` |
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
