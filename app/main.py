"""
pdf-extractext — Punto de entrada principal.

Flujo:
  1. Leer configuración desde variables de entorno.
  2. Recibir ruta(s) de PDF como argumento CLI.
  3. Extraer texto del PDF.
  4. Generar resumen con IA.
  5. Guardar resultado en MongoDB.
"""

import sys
import logging

# TODO (Issue #8): El logging se configurará en detalle en el issue de logging.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)


def main() -> None:
    """Función principal del pipeline de extracción y resumen."""
    logger.info("pdf-extractext iniciado.")

    # TODO (Issue #5): Integrar extractor de PDF.
    # TODO (Issue #6): Integrar módulo de resumen con IA.
    # TODO (Issue #4): Guardar resultado en MongoDB.

    logger.info("Pipeline completado.")


if __name__ == "__main__":
    main()
