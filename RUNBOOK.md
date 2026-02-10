## Runbook de despliegue (local -> EC2)

Objetivo
Validar el flujo en local y migrar a EC2 cuando haya estabilidad suficiente.

### Fase 1: Validacion local

Checklist inicial
- Docker Desktop instalado y activo.
- Imagen Docker construida localmente.
- Carpeta local para `data/` y `logs/`.
- `.env` local con credenciales de Peritoline.

Ejecucion local recomendada (manual)
```powershell
docker run --rm ^
  --env-file C:\notas-reply\.env ^
  -e PIPELINE_MODELO=241 ^
  -e PIPELINE_SKIP_GENERALI=true ^
  -e PIPELINE_PERITOS="MARIA VELAZQUEZ,ENRIQUE GONZALEZ,MIGUEL FUSTES" ^
  -v C:\notas-reply\logs:/app/logs ^
  -v C:\notas-reply\data:/app/data ^
  notas-reply:latest
```

Programador de tareas (Windows)
1) Abre "Programador de tareas".
2) Crea tarea basica.
3) Disparador: Diario, repetir cada 1 hora entre 09:00 y 18:00.
4) Accion: Iniciar un programa.
5) Programa: `powershell.exe`
6) Argumentos:
```
-NoProfile -ExecutionPolicy Bypass -Command "docker run --rm --env-file C:\notas-reply\.env -e PIPELINE_MODELO=241 -e PIPELINE_SKIP_GENERALI=true -e PIPELINE_PERITOS=\"MARIA VELAZQUEZ,ENRIQUE GONZALEZ,MIGUEL FUSTES\" -v C:\notas-reply\logs:/app/logs -v C:\notas-reply\data:/app/data notas-reply:latest"
```

Monitoreo diario
- Revisar `logs/app.log`.
- Verificar que `data/pending_*.jsonl` se vacia tras ejecuciones OK.
- Revisar tiempos de ejecucion (no mas de 20-30 min por ciclo).

Criterios para pasar a EC2
- 2 semanas con >95% de ejecuciones OK.
- Fallos recuperados en la siguiente ejecucion.
- No hay bloqueos persistentes en portales.

### Fase 2: Preparacion EC2

Checklist de migracion
- Imagen en ECR con tag estable.
- `.env` listo para EC2 (sin APP_*).
- Carpeta `/opt/notas-reply/data` y `/opt/notas-reply/logs`.
- Zona horaria `Europe/Stockholm`.

Verificacion previa
- Pull de la imagen y ejecucion manual exitosa.
- Logs escritos en `/opt/notas-reply/logs`.

### Fase 3: Operacion en EC2

Cron recomendado
```cron
0 8-22 * * * docker run --rm --env-file /opt/notas-reply/.env -e PIPELINE_MODELO=241 -e PIPELINE_SKIP_GENERALI=true -e PIPELINE_PERITOS="MARIA VELAZQUEZ,ENRIQUE GONZALEZ,MIGUEL FUSTES" -v /opt/notas-reply/logs:/app/logs -v /opt/notas-reply/data:/app/data <ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/notas-reply:latest
```

Supervision inicial (primeras 48h)
- Revisar logs cada 3-4 horas.
- Verificar que el pipeline se completa y que no quedan pendientes bloqueados.
- Ajustar `APP_SLOW_MO_MS` o `APP_HEADLESS` si hay fallos.

### Diagnostico rapido

Si el flujo se queda en un portal
- Revisar logs para el ultimo paso ejecutado.
- Reintentar en la siguiente ejecucion (el pending conserva las notas).
- Subir `APP_SLOW_MO_MS` y bajar el ritmo de ejecucion.

Si falla el login
- Confirmar credenciales de Peritoline.
- Verificar si hay captcha o bloqueo temporal.
- El pipeline debe continuar con el siguiente portal.

### Registro de cambios

Mantener una nota simple con:
- Fecha
- Cambio aplicado
- Resultado
