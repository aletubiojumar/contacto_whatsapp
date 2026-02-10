# Guia de despliegue en EC2 (Amazon Linux) con Docker + ECR

Esta guia explica como dockerizar, subir a ECR y ejecutar el pipeline en EC2
cada hora de 08:00 a 22:00 (Europe/Stockholm). Incluye el modo inicial para
generar JSONL dos veces seguidas y luego el cron normal.

## 0) Requisitos previos

- Cuenta AWS con permisos para ECR y EC2.
- AWS CLI instalado en tu PC y configurado (`aws configure`).
- Un EC2 con Amazon Linux en `eu-north-1`.
- Un repositorio ECR creado.

## 1) Preparar el repo local

1. Asegurate de tener el repo actualizado.
2. El contenedor usa Chromium en headless (default).
3. Variables requeridas en un `.env` (ver ejemplo mas abajo).

## 2) Crear repositorio en ECR

```bash
aws ecr create-repository --repository-name notas-reply --region eu-north-1
```

Obten tu `ACCOUNT_ID`:
```bash
aws sts get-caller-identity --query Account --output text
```

## 3) Build de la imagen Docker (local)

Desde la raiz del repo:
```bash
docker build -t notas-reply:latest .
```

## 4) Login y push a ECR (local)

```bash
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com
docker tag notas-reply:latest <ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/notas-reply:latest
docker push <ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/notas-reply:latest
```

## 5) Preparar EC2 (Amazon Linux)

Conectate por SSH y ejecuta:
```bash
sudo yum update -y
sudo amazon-linux-extras install docker -y
sudo service docker start
sudo usermod -a -G docker ec2-user
```

Cierra la sesion SSH y entra de nuevo para aplicar el grupo `docker`.

## 6) Crear carpetas de trabajo en EC2

```bash
mkdir -p /opt/notas-reply/logs
mkdir -p /opt/notas-reply/data
```

## 7) Crear archivo .env en EC2

Crea `/opt/notas-reply/.env` con estas variables:

```ini
# Peritoline
PERITOLINE_LOGIN_URL=...
PERITOLINE_USERNAME=...
PERITOLINE_PASSWORD=...

Nota: no se requieren credenciales ePAC en el .env, se leen desde Peritoline > Claves.

# Opcionales (recomendado)
APP_HEADLESS=true
APP_SLOW_MO_MS=0
APP_KEEP_BROWSER_OPEN=false
APP_MIN_ACTION_DELAY_S=0.6
APP_MAX_ACTION_DELAY_S=2.4
APP_NAV_TIMEOUT_MS=30000
APP_SUBMIT_TIMEOUT_MS=120000

# Logging
LOG_DIR=logs
LOG_BACKUP_COUNT=30
```

## 8) Login a ECR y pull en EC2

Si el EC2 tiene rol con permisos ECR, basta:
```bash
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com
docker pull <ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/notas-reply:latest
```

## 9) Ejecucion inicial (dos veces JSONL)

La primera vez queremos generar JSONL dos veces seguidas:
```bash
docker run --rm \
  --env-file /opt/notas-reply/.env \
  -e PIPELINE_MODELO=241 \
  -e PIPELINE_SKIP_GENERALI=true \
  -e PIPELINE_PERITOS="MARIA VELAZQUEZ,ENRIQUE GONZALEZ,MIGUEL FUSTES" \
  -v /opt/notas-reply/logs:/app/logs \
  -v /opt/notas-reply/data:/app/data \
  <ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/notas-reply:latest \
  bash -lc "python scripts/run_download_and_build_jsonl.py --modelo 241 --peritos \"MARIA VELAZQUEZ,ENRIQUE GONZALEZ,MIGUEL FUSTES\" && sleep 5 && python scripts/run_download_and_build_jsonl.py --modelo 241 --peritos \"MARIA VELAZQUEZ,ENRIQUE GONZALEZ,MIGUEL FUSTES\""
```

## 10) Ejecucion normal del pipeline (manual)

```bash
docker run --rm \
  --env-file /opt/notas-reply/.env \
  -e PIPELINE_MODELO=241 \
  -e PIPELINE_SKIP_GENERALI=true \
  -e PIPELINE_PERITOS="MARIA VELAZQUEZ,ENRIQUE GONZALEZ,MIGUEL FUSTES" \
  -v /opt/notas-reply/logs:/app/logs \
  -v /opt/notas-reply/data:/app/data \
  <ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/notas-reply:latest
```

## 11) Programar cron (08:00 a 22:00)

Configura zona horaria:
```bash
sudo timedatectl set-timezone Europe/Stockholm
```

Edita el cron:
```bash
crontab -e
```

Agrega:
```cron
0 8-22 * * * docker run --rm --env-file /opt/notas-reply/.env -e PIPELINE_MODELO=241 -e PIPELINE_SKIP_GENERALI=true -e PIPELINE_PERITOS="MARIA VELAZQUEZ,ENRIQUE GONZALEZ,MIGUEL FUSTES" -v /opt/notas-reply/logs:/app/logs -v /opt/notas-reply/data:/app/data <ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/notas-reply:latest
```

## 12) Logs y datos

- Logs: `/opt/notas-reply/logs`
- Excel/JSONL/pending: `/opt/notas-reply/data`

## 13) Actualizar a nueva version

1. Build + push de imagen nueva (pasos 3 y 4).
2. En EC2:
```bash
docker pull <ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/notas-reply:latest
```
El cron ya usara la imagen actualizada en la siguiente hora.
