#!/bin/sh
# Prueba de carga fija (modelo abierto) con el perfil de la cátedra:
# 50 req/s durante 30 s, timeout de 30 s, rotando los 4 PDFs de targets.txt.
set -eu

RATE="${RATE:-50}"
DURATION="${DURATION:-30s}"
TIMEOUT="${TIMEOUT:-30s}"
RESULTS=/stress/results

vegeta attack \
  -targets=/stress/vegeta/targets.txt \
  -rate="$RATE" \
  -duration="$DURATION" \
  -timeout="$TIMEOUT" \
  | tee "$RESULTS/vegeta-results.bin" \
  | vegeta report

vegeta report -type=json < "$RESULTS/vegeta-results.bin" > "$RESULTS/vegeta-report.json"
vegeta plot < "$RESULTS/vegeta-results.bin" > "$RESULTS/vegeta-plot.html"
