#!/bin/bash
set -euo pipefail

# Ajusta esto si quieres:
export DB_NAME="criteria_peritoline"

# Importante: apunta al my.cnf del entorno (en AWS será otro path)
# Debe incluir host/user/ssl/ssl-ca/ssl-cert/ssl-key etc.
export DB_DEFAULTS_FILE="$HOME/.my.cnf"

OUT="${1:-allianz_filtrado.xlsx}"
python3 export_allianz_query_to_excel.py "$OUT"
