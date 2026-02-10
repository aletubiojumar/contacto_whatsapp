# Proyecto Allianz / ePAC

## Resumen
Este proyecto automatiza todo el flujo Allianz a ePAC sin pasos manuales:

1. Consulta directa a **Peritoline (BD)** mediante una **query única en producción**.
2. Generación directa del **Excel filtrado** (sin `filter_excel.py`).
3. Obtención de **credenciales ePAC desde BD** (tabla `softline_aseguradoras_claves_web`).
4. Acceso a **ePAC con Playwright (headless)**.
5. Navegación automática por peritaciones y **extracción de teléfonos**.

---

## Cambios importantes (enero 2026)

### Eliminado filtrado por Excel
- `filter_excel.py` eliminado.
- El filtrado se hace 100% en SQL.
- El Excel ya sale listo para usar desde la BD.

Columnas del Excel generado:
- `Encargo`
- `Fecha Sin.`
- `Causa`
- `Aseguradora`
Tras la extracción de teléfonos se añaden las columnas `Teléfono` y `Estado`.

---

## Script principal Allianz (BD a Excel)

```bash
python3 scripts/export_allianz_from_db.py --out data/peritoline/raw_allianz/allianz_report_latest.xlsx
```

Este script:
- Lee credenciales de BD desde `.env`.
- Usa conexión MySQL con SSL compatible.
- Ejecuta la query final de producción.
- Genera el Excel final.

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

- No necesita XServer.
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
```

Notas:
- `mysql-connector-python`
- `use_pure=True`
- `charset='latin1'`
- SSL sin verificación estricta

---

## Flujo completo recomendado

```bash
# 1. Generar Excel desde BD
python3 scripts/export_allianz_from_db.py --out data/peritoline/raw_allianz/allianz_report_latest.xlsx

# 2. Extraer teléfonos desde ePAC
python3 scripts/extraer_teléfonos_epac.py --headless
```

---

Sistema ahora determinista, reproducible y sin pasos manuales.
Toda la lógica de negocio vive en la BD.
Playwright solo se usa donde aporta valor (ePAC).

## Estructura del proyecto
- `scripts/export_allianz_from_db.py`: Exporta siniestros desde BD a Excel y dispara la extracción ePAC.
- `scripts/extraer_teléfonos_epac.py`: Lee el Excel y extrae teléfonos desde ePAC.
- `peritoline/`: Integración con Peritoline, query y utilidades de extracción.
- `epac/`: Page Objects y workflow para navegar ePAC.
- `config.py`: Carga de configuración y variables de entorno comunes.
- `browser.py`: Lanzador de navegador Playwright.
- `data/`: Archivos de salida (Excel y resúmenes).
