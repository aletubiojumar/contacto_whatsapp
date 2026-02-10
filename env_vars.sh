#!/bin/bash
# Variables de entorno para ejecutar en el servidor AWS
# Uso: source env_vars.sh

# Base de Datos
export DB_HOST=criteria-db.softline.es
export DB_PORT=3306
export DB_USER=remote-esail
export DB_PASS=wR.Kuq70ZH@k9otZGGX_R1j4UMIrbDqE
export DB_NAME=criteria_peritoline

# ⚠️ IMPORTANTE: Rutas SSL deben apuntar a /app/certs/ (dentro del contenedor)
export DB_SSL_CA=/app/certs/ca.pem
export DB_SSL_CERT=/app/certs/client-cert.pem
export DB_SSL_KEY=/app/certs/client-key.pem
export DB_SSL_VERIFY_SERVER_CERT=false
export DB_SSL_REQUIRED=true

# Peritoline
export PERITOLINE_LOGIN_URL=https://peritolinecloud.criteriaicla.net/softline/login
export PERITOLINE_USERNAME=ATUBIO
export PERITOLINE_PASSWORD=ATUBIO

# Pipeline
export PIPELINE_MODELO=epac

# Opcionales
export APP_HEADLESS=false
export APP_SLOW_MO_MS=250
export APP_KEEP_BROWSER_OPEN=false
export APP_MIN_ACTION_DELAY_S=0.6
export APP_MAX_ACTION_DELAY_S=2.4
export APP_NAV_TIMEOUT_MS=30000
export APP_SUBMIT_TIMEOUT_MS=120000
export LOG_DIR=logs
export LOG_BACKUP_COUNT=30
export PYTHON_API_URL=http://localhost:5000

echo "✓ Variables de entorno exportadas"
echo "Ejecuta: ./deploy_aws.sh"
