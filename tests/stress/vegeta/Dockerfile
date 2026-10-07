# Vegeta no publica una imagen oficial: se compila desde su repositorio con versión fija.
FROM golang:1.23-alpine AS build
RUN go install github.com/tsenart/vegeta/v12@v12.12.0

FROM alpine:3.20
COPY --from=build /go/bin/vegeta /usr/local/bin/vegeta
