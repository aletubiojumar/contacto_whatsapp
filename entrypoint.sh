#!/usr/bin/env bash
set -euo pipefail
export APP_HEADLESS=${APP_HEADLESS:-true}
export APP_SLOW_MO_MS=${APP_SLOW_MO_MS:-0}
export APP_KEEP_BROWSER_OPEN=${APP_KEEP_BROWSER_OPEN:-false}

# ✅ Si ECS (CMD) manda un comando, ejecútalo tal cual
if [[ $# -gt 0 ]]; then
  exec "$@"
fi

# 🔁 Si no hay comando, mantener contenedor corriendo
exec tail -f /dev/null
