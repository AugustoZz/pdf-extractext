#!/bin/sh
# Carga la configuración inicial de documents-service en el KV de Consul.
# Corre una vez, antes que la API (servicio consul-init del compose).
# Cambiar un valor en la UI de Consul (http://localhost:8500) y reiniciar la
# API alcanza para aplicarlo, sin tocar el compose ni reconstruir la imagen.
set -eu

PREFIX="config/pdf-extractext"

consul kv put "$PREFIX/LOG_LEVEL" "INFO"
consul kv put "$PREFIX/MAX_FILE_SIZE_MB" "10"
consul kv put "$PREFIX/EXTRACTOR_TIMEOUT_SECONDS" "30"
consul kv put "$PREFIX/CIRCUIT_BREAKER_FAILURE_THRESHOLD" "5"
consul kv put "$PREFIX/CIRCUIT_BREAKER_RECOVERY_SECONDS" "30"

echo "Configuración cargada en Consul bajo $PREFIX/"
