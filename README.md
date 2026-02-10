# Proyecto Allianz / ePAC

## Resumen
Este proyecto automatiza todo el flujo para sacar los datos del asegurado sin pasos manuales:

1. Consulta directa a **Peritoline (BD)** mediante una **query única**.
2. Generación directa del **Excel filtrado**.
3. Obtención de **credenciales ePAC desde BD** (tabla `softline_aseguradoras_claves_web`).
4. Acceso a **ePAC con Playwright (headless)**.
5. Navegación automática por peritaciones y **extracción de teléfonos**.

---

## Script principal ePAC (Excel a Teléfonos)

```bash
python3 scripts/extraer_teléfonos_epac.py --headless
```

Este script:
1. Lee el Excel generado por `export_allianz_from_db.py`.
2. Obtiene **credenciales ePAC desde BD** (`softline_aseguradoras_claves_web`).
3. Lanza Playwright **en modo headless**.
4. Hace login en ePAC.
5. Navega por *Peritaciones Diversos*.
6. Busca cada siniestro.
7. Extrae teléfonos y genera salida final.

---

## Credenciales ePAC

Las credenciales **NO se configuran a mano**.

Se obtienen automáticamente desde BD:

```sql
SELECT user, pass, url
FROM softline_aseguradoras_claves_web
WHERE id_cia IN (42, 399);
```

Fallback:
- CLI `mysql/mariadb` local
- Variables de entorno solo si falla todo

---

## Playwright

- Se ejecuta siempre con:

```bash
--headless
```

- No se usa Playwright para Peritoline, **solo para ePAC**.

---

## Variables de entorno requeridas (.env)

```env
DB_HOST=
DB_NAME=
DB_USER=
DB_PASS=
DB_PORT=
DB_SSL_CA=
DB_SSL_CERT=
DB_SSL_KEY=

PERITOLINE_LOGIN_URL=
PERITOLINE_USERNAME=
PERITOLINE_PASSWORD=
```

Notas:
- `mysql-connector-python`
- `use_pure=True`
- `charset='latin1'`
- SSL sin verificación estricta

---
