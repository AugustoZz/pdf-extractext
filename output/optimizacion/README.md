# Entrega de la optimización — 08/10/2026

> El parche y el ZIP incorporan ahora límites de generadores y el complemento
> TLS. Las [pruebas finales por el host Linux](../../docs/carga-host-linux-2026-10-08.md)
> superan las referencias publicadas. También se conservan los malos resultados
> por el gateway Windows; `final-1/` y `final-2/` son históricos por HTTP interno.

El [informe completo](../../docs/optimizacion-2026-10-08.md) compara la versión
anterior, dos repeticiones finales y la referencia del profesor. Las subcarpetas
`final-1/` y `final-2/` contienen los JSON, dashboards de k6 y gráficos de Vegeta.
Los binarios originales se conservan localmente y están excluidos de Git.

## Incorporar los cambios al repositorio del extractor

`extractor.patch` contiene código, tests, configuración, scripts de la cátedra y
evidencia; parte del commit `236829facd728b0216f421f2598e0c9d3598fbd8` de
`https://github.com/valendotjpg/pdf-extractext-extractor`.

Desde el checkout de ese repositorio, con el parche descargado:

```bash
git apply --check /ruta/extractor.patch
git apply /ruta/extractor.patch
uv run pytest
docker compose up --build -d
```

El ZIP `extractor-optimizado.zip` contiene el repositorio completo con los cambios,
sin `.git`, entornos virtuales, PDFs ni binarios de carga. Incluye `uv.lock`, los
27 tests y los perfiles necesarios para reproducir la prueba. Los PDFs deben
copiarse a `tests/stress/pdfs/` con los nombres indicados en su README.

En esta PC el proyecto principal ya usa la copia optimizada en `.test-extractor`,
seleccionada mediante `.env`. Los cambios de ambos repositorios son locales:
para que la entrega de GitHub incluya la mejora, hay que incorporar el parche
al repositorio del extractor y publicar los cambios de documents-service.
