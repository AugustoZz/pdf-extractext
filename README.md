# 📄 pdf-extractext

> Aplicación web para extracción de texto desde archivos PDF, con persistencia en base de datos no relacional y gestión CRUD de documentos. Inspirado en ILovePDF.

**Universidad Tecnológica Nacional — Facultad Regional San Rafael**
**Ingeniería en Sistemas | Desarrollo de Software 2026**

---

## 📋 Descripción

`pdf-extractext` permite a los usuarios enviar archivos PDF y obtener el texto extraído. El sistema valida el archivo, genera un checksum para evitar duplicados y persiste el contenido en una base de datos no relacional (MongoDB). Expone una API REST construida con FastAPI.

---

## 🚀 Tecnologías

| Tecnología | Uso |
|---|---|
| **Python 3.12+** | Lenguaje principal |
| **FastAPI** | Framework web / API REST |
| **uv** | Gestor de paquetes y entornos virtuales |
| **MongoDB** | Base de datos no relacional |
| **pdfplumber** | Extracción de texto desde PDFs |
| **pytest** | Testing (TDD) |

---

## 🏗️ Arquitectura del Proyecto

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
├── tests/                      # Suite de pruebas (TDD)
│   ├── unit/                   # Pruebas unitarias
│   └── integration/            # Pruebas de integración
│
├── docs/                       # Documentación del proyecto
├── .env.example                # Variables de entorno requeridas (12-Factor)
├── pyproject.toml              # Configuración del proyecto y dependencias
└── README.md
```

---

## ⚙️ Configuración (12-Factor App)

Copia `.env.example` a `.env` y completa los valores:

```bash
cp .env.example .env
```

> ⚠️ **Nunca subas `.env` al repositorio.** Ya está incluido en `.gitignore`.

---

## 🛠️ Instalación y Ejecución

### Requisitos previos
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) instalado

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/AugustoZz/pdf-extractext.git
cd pdf-extractext

# 2. Crear entorno virtual e instalar dependencias
uv sync

# 3. Configurar variables de entorno
cp .env.example .env

# 4. Ejecutar la aplicación
uv run uvicorn app.main:app --reload
```

La API estará disponible en `http://localhost:8000`
Documentación interactiva en `http://localhost:8000/docs`

---

## 🧪 Testing (TDD)

Este proyecto aplica **Test Driven Development**. Las pruebas se ejecutan con:

```bash
uv run pytest
```

```bash
# Solo pruebas unitarias
uv run pytest tests/unit/

# Solo pruebas de integración
uv run pytest tests/integration/

# Con cobertura
uv run pytest --cov=app
```

---

## 🌐 Endpoints de la API

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/v1/documents/` | Subir y extraer texto de un PDF |
| `GET` | `/api/v1/documents/` | Listar todos los documentos |
| `GET` | `/api/v1/documents/{id}` | Obtener documento por ID |
| `PUT` | `/api/v1/documents/{id}` | Actualizar documento |
| `DELETE` | `/api/v1/documents/{id}` | Eliminar documento |

---

## 📐 Principios Aplicados

- **12-Factor App** — Configuración por variables de entorno, dependencias explícitas, procesos sin estado
- **TDD** — Test Driven Development con pytest
- **SOLID** — Principios de diseño orientado a objetos
- **DRY** — Don't Repeat Yourself
- **KISS** — Keep It Simple, Stupid
- **YAGNI** — You Aren't Gonna Need It
- **Clean Architecture** — Separación de capas (API → Services → Infrastructure)

---

## 📦 Los 12 Factores

| Factor | Implementación |
|--------|----------------|
| **I. Codebase** | Un repositorio Git, múltiples deploys |
| **II. Dependencies** | `pyproject.toml` + `uv` — dependencias declaradas explícitamente |
| **III. Config** | Variables de entorno vía `.env` (nunca en código) |
| **IV. Backing Services** | MongoDB como recurso adjunto configurable |
| **V. Build/Release/Run** | Separación clara de etapas |
| **VI. Processes** | La app es stateless — no guarda estado entre requests |
| **VII. Port Binding** | FastAPI expone el servicio vía puerto configurable |
| **VIII. Concurrency** | Escalable horizontalmente con workers uvicorn |
| **IX. Disposability** | Arranque rápido, cierre limpio |
| **X. Dev/Prod Parity** | Mismo stack en dev y prod |
| **XI. Logs** | Tratados como streams de eventos (stdout) |
| **XII. Admin Processes** | Tareas de gestión como procesos independientes |

---

## 🤝 Contribución

1. Crear un Issue describiendo la mejora o bug
2. Crear una rama: `git checkout -b feature/nombre-feature`
3. Hacer commits descriptivos
4. Abrir un Pull Request referenciando el Issue

---

## 📅 Plazo de Entrega

**23/05/2025** — Etapa N°1

---

## 📄 Licencia

MIT © 2026 — Universidad Tecnológica Nacional

<h1>pdf-extractext</h1>

"""<p>
  Script en Python para extraer texto de archivos PDF y resumirlos con uso de IA (Agente a definir).
</p>

<h2>Tecnologías</h2>
<ul>
  <li><strong>Lenguaje:</strong> Python</li>
  <li><strong>IA:</strong> Modelo a elegir</li>
  <li><strong>Base de Datos:</strong> MongoDB</li>
  <li><strong>Gestor de Paquetes:</strong> UV</li>
  <li><strong>Librerías de Extracción:</strong> 
    <ul>
      <li>pdfplumber</li>
      <li>PyPDF2 3.0.1</li>
    </ul>
  </li>
</ul>

<h2>Metodologías</h2>
<ul>
  <li><strong>TDD:</strong> Test Driven Development</li>
  <li><strong>12 Factores:</strong> Principios de programación para aplicaciones modernas</li>
</ul>"""