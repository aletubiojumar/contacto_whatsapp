#!/bin/bash
set -e

echo "=== Despliegue de Contenedor Python con SSL ==="

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Directorio del proyecto
PROJECT_DIR="$HOME/notas-reply"
cd "$PROJECT_DIR"

echo -e "${YELLOW}1. Verificando certificados SSL...${NC}"
if [ ! -d "certs" ]; then
    echo -e "${RED}ERROR: No existe el directorio certs/${NC}"
    exit 1
fi

# Renombrar certificados si es necesario
if [ -f "certs/softline-criteria-db-ca.pem" ] && [ ! -f "certs/ca.pem" ]; then
    echo "Renombrando certificados..."
    mv certs/softline-criteria-db-ca.pem certs/ca.pem
    mv certs/softline-criteria-db-client-cert.pem certs/client-cert.pem
    mv certs/softline-criteria-db-client-key.pem certs/client-key.pem
fi

# Verificar que existan los certificados
if [ ! -f "certs/ca.pem" ] || [ ! -f "certs/client-cert.pem" ] || [ ! -f "certs/client-key.pem" ]; then
    echo -e "${RED}ERROR: Faltan certificados SSL en certs/${NC}"
    ls -la certs/
    exit 1
fi

echo -e "${GREEN}✓ Certificados encontrados${NC}"

echo -e "${YELLOW}2. Verificando variables de entorno...${NC}"
if [ -z "$DB_HOST" ]; then
    echo -e "${YELLOW}⚠ Variables de entorno no detectadas en el shell actual${NC}"
    echo -e "${YELLOW}⚠ Asegúrate de configurarlas antes de ejecutar docker run${NC}"
fi

echo -e "${YELLOW}3. Deteniendo contenedor anterior...${NC}"
docker stop chatbot_whatsapp 2>/dev/null || true
docker rm chatbot_whatsapp 2>/dev/null || true
docker stop notas-reply-python 2>/dev/null || true
docker rm notas-reply-python 2>/dev/null || true
echo -e "${GREEN}✓ Contenedores anteriores eliminados${NC}"

echo -e "${YELLOW}4. Construyendo nueva imagen Docker...${NC}"
docker build -t notas-reply-python .
echo -e "${GREEN}✓ Imagen construida${NC}"

echo -e "${YELLOW}5. Creando directorios necesarios...${NC}"
mkdir -p "$PROJECT_DIR/data/peritoline/raw_allianz"
mkdir -p "$PROJECT_DIR/logs"
echo -e "${GREEN}✓ Directorios creados${NC}"

echo -e "${YELLOW}6. Iniciando contenedor...${NC}"
echo -e "${YELLOW}Nota: Las variables de entorno deben estar configuradas en AWS${NC}"

# Iniciar contenedor con variables de entorno desde AWS
docker run -d \
  --name notas-reply-python \
  -e PIPELINE_MODELO="${PIPELINE_MODELO:-epac}" \
  -e DB_HOST="${DB_HOST:-criteria-db.softline.es}" \
  -e DB_PORT="${DB_PORT:-3306}" \
  -e DB_USER="${DB_USER:-remote-esail}" \
  -e DB_PASS="${DB_PASS}" \
  -e DB_NAME="${DB_NAME:-criteria_peritoline}" \
  -e DB_SSL_CA="/app/certs/ca.pem" \
  -e DB_SSL_CERT="/app/certs/client-cert.pem" \
  -e DB_SSL_KEY="/app/certs/client-key.pem" \
  -e DB_SSL_VERIFY_SERVER_CERT=false \
  -e DB_SSL_REQUIRED=true \
  -v "$PROJECT_DIR/data:/app/data" \
  -v "$PROJECT_DIR/logs:/tmp" \
  notas-reply-python

echo -e "${GREEN}✓ Contenedor iniciado${NC}"

echo -e "${YELLOW}7. Esperando 5 segundos...${NC}"
sleep 5

echo -e "${YELLOW}8. Verificando estado del contenedor...${NC}"
if docker ps | grep -q notas-reply-python; then
    echo -e "${GREEN}✓ Contenedor corriendo correctamente${NC}"
else
    echo -e "${RED}ERROR: El contenedor no está corriendo${NC}"
    echo "Logs del contenedor:"
    docker logs notas-reply-python
    exit 1
fi

echo -e "${YELLOW}9. Verificando certificados dentro del contenedor...${NC}"
docker exec notas-reply-python ls -la /app/certs/

echo -e "${YELLOW}10. Verificando variables de entorno SSL...${NC}"
docker exec notas-reply-python sh -c 'echo "DB_SSL_CA=$DB_SSL_CA"'
docker exec notas-reply-python sh -c 'echo "DB_SSL_CERT=$DB_SSL_CERT"'
docker exec notas-reply-python sh -c 'echo "DB_SSL_KEY=$DB_SSL_KEY"'

echo -e "${YELLOW}11. Probando conexión a la base de datos...${NC}"
docker exec notas-reply-python python3 /app/scripts/export_allianz_from_db.py \
  --out /app/data/test_connection.xlsx

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓✓✓ DESPLIEGUE EXITOSO ✓✓✓${NC}"
    echo ""
    echo "Comandos útiles:"
    echo "  Ver logs:          docker logs -f notas-reply-python"
    echo "  Reiniciar:         docker restart notas-reply-python"
    echo "  Entrar al shell:   docker exec -it notas-reply-python sh"
    echo "  Ejecutar script:   docker exec notas-reply-python python3 /app/scripts/export_allianz_from_db.py --out /app/data/output.xlsx"
else
    echo -e "${RED}ERROR: Falló la prueba de conexión${NC}"
    echo "Ver logs detallados con: docker logs notas-reply-python"
    exit 1
fi
