# Registro de servicios en Consul.
#
# El extractor vive en otro repositorio y no se registra solo: lo registramos
# desde acá, apuntando a su punto de entrada (el balanceador extractor-lb, que
# reparte entre las réplicas). Consul consulta /health cada 5 s; si falla,
# deja de devolverlo como instancia sana y la API responde 503 sin llamarlo.

services {
  name    = "extractor"
  id      = "extractor-lb"
  address = "extractor-lb"
  port    = 80
  tags    = ["pdf", "extraccion"]

  check {
    id       = "extractor-http"
    name     = "GET /health del extractor"
    http     = "http://extractor-lb/health"
    interval = "5s"
    timeout  = "2s"
  }
}

services {
  name    = "documents"
  id      = "documents-api"
  address = "api"
  port    = 8000
  tags    = ["api", "crud"]

  check {
    id       = "documents-http"
    name     = "GET /health de la API"
    http     = "http://api:8000/health"
    interval = "10s"
    timeout  = "2s"
  }
}
