"""Pipeline completo: descarga, diff, JSONL y ejecucion de notas."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from browser import launch_browser  # noqa: E402
from config import AppConfig, load_config  # noqa: E402
from peritoline.downloader import download_report_in_session  # noqa: E402
from peritoline.login_page import PeritolineLoginPage  # noqa: E402
from peritoline.navigation_page import PeritolineNavigationPage  # noqa: E402
from pipeline.build_notas import build_jsonl  # noqa: E402
from processing.diff import compute_contact_changes  # noqa: E402
from processing.excel_parser import normalize_text, parse_report  # noqa: E402
from ama.workflow import run_ama_with_page  # noqa: E402
from generali.workflow import run_generali_with_page  # noqa: E402
from utils.human import human_delay  # noqa: E402
from utils.logging_utils import get_logger, setup_logging  # noqa: E402
from playwright.sync_api import Page  # noqa: E402
from epac.workflow import run_workflow_with_page  # noqa: E402


def _prune_old_reports(base_dir: Path, keep: int = 3) -> None:
    """Mantiene solo los ultimos N reportes con timestamp.

    Args:
        base_dir: Carpeta donde se guardan los reportes.
        keep: Numero de reportes a conservar.

    Returns:
        None.
    """

    reports = sorted(base_dir.glob("*_report_*.xlsx"), reverse=True)
    for path in reports[keep:]:
        path.unlink(missing_ok=True)


def _prepare_paths(prefix: str) -> tuple[Path, Path, Path | None]:
    """Prepara rutas de salida y copia el ultimo reporte como anterior.

    Args:
        prefix: Prefijo del reporte (allianz o generali).

    Returns:
        Ruta del nuevo reporte, ruta del ultimo reporte y ruta del anterior (si existe).
    """

    base_dir = Path(f"data/peritoline/raw_{prefix}")
    base_dir.mkdir(parents=True, exist_ok=True)

    latest_path = base_dir / f"{prefix}_report_latest.xlsx"
    previous_path = base_dir / f"{prefix}_report_previous.xlsx"
    if latest_path.exists():
        shutil.copy2(latest_path, previous_path)
    else:
        previous_path = None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = base_dir / f"{prefix}_report_{timestamp}.xlsx"
    return output_path, latest_path, previous_path


def _parse_peritos(value: str) -> list[str]:
    """Convierte una lista separada por comas en peritos normalizados.

    Args:
        value: Cadena con nombres separados por coma.

    Returns:
        Lista de peritos normalizados.
    """

    if not value:
        return []
    return [normalize_text(item) for item in value.split(",") if item.strip()]


def _match_perito(cell_value: str, peritos: set[str]) -> bool:
    """Verifica si la celda contiene alguno de los peritos objetivo.

    Args:
        cell_value: Texto de peritos en el Excel.
        peritos: Conjunto de peritos normalizados.

    Returns:
        True si hay coincidencia, False si no.
    """

    if not peritos:
        return True
    normalized = normalize_text(cell_value)
    if normalized in peritos:
        return True
    parts = [part.strip() for part in cell_value.split("-") if part.strip()]
    for part in parts:
        if normalize_text(part) in peritos:
            return True
    return False


def _load_jsonl(path: Path) -> list[dict]:
    """Carga un JSONL si existe y devuelve sus entradas.

    Args:
        path: Ruta del archivo JSONL.

    Returns:
        Lista de diccionarios con las notas.
    """

    if not path.exists():
        return []
    notas: list[dict] = []
    with path.open("r", encoding="utf-8-sig") as fh:
        for line in fh:
            stripped = line.strip()
            if not stripped:
                continue
            notas.append(json.loads(stripped))
    return notas


def _merge_pending_notes(
    pending: list[dict], new_notes: list[dict], key_fields: tuple[str, ...]
) -> list[dict]:
    """Mezcla notas pendientes con nuevas y prioriza las nuevas.

    Args:
        pending: Lista de notas pendientes.
        new_notes: Lista de notas nuevas.
        key_fields: Campos usados para deduplicar.

    Returns:
        Lista combinada de notas.
    """

    seen = set()
    merged: list[dict] = []
    for nota in new_notes + pending:
        key = tuple(str(nota.get(field, "")) for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        merged.append(nota)
    return merged


def _merge_and_persist_pending(
    pending_path: Path, new_notes: list[dict], key_fields: tuple[str, ...]
) -> list[dict]:
    """Actualiza el archivo de pendientes y devuelve la cola final.

    Args:
        pending_path: Ruta del JSONL de pendientes.
        new_notes: Notas nuevas a agregar.
        key_fields: Campos usados para deduplicar.

    Returns:
        Lista final de pendientes.
    """

    pending = _load_jsonl(pending_path)
    merged = _merge_pending_notes(pending, new_notes, key_fields)
    if merged:
        build_jsonl(merged, pending_path)
    else:
        pending_path.unlink(missing_ok=True)
    return merged


def _volver_a_peritoline(page: Page, config: AppConfig, logger) -> None:
    """Lleva el foco a Peritoline tras un error de aseguradora.

    Args:
        page: Pagina activa de Peritoline.
        config: Configuracion de la aplicacion.
        logger: Logger asociado al flujo.

    Returns:
        None.
    """

    try:
        human_delay(config, "Volviendo a Peritoline")
        page.bring_to_front()
        page.wait_for_load_state("domcontentloaded")
    except Exception:
        if logger:
            logger.warning("No se pudo devolver el foco a Peritoline")


def _build_text_allianz(visita: str) -> str:
    """Construye el texto de la nota de Allianz segun la visita.

    Args:
        visita: Fecha de visita en formato libre.

    Returns:
        Texto final de la nota.
    """

    if visita:
        return f"Se ha concertado intervencion para fecha {visita}"
    return "Se ha contactado con el asegurado"


def _build_text_ama(visita: str) -> str:
    """Construye el texto de la nota de AMA segun la visita.

    Args:
        visita: Fecha de visita en formato libre.

    Returns:
        Texto final de la nota.
    """

    if visita:
        return f"Intervencion concertada para la fecha {visita}."
    return (
        "Se ha contactado con el Mutualista a la espera de concretar fecha intervencion."
    )


def _build_text_generali(visita: str) -> str:
    """Construye el texto de la nota de Generali segun la visita.

    Args:
        visita: Fecha de visita en formato libre.

    Returns:
        Texto final de la nota.
    """

    if visita:
        return f"Intervencion fijada para la fecha {visita}."
    return "Contacto con el asegurado realizado."


def _cerrar_popup_avisos_si_existe(page: Page, config: AppConfig) -> None:
    """Cierra el popup de avisos si aparece tras el login.

    Args:
        page: Pagina activa.
        config: Configuracion con pausas humanas.

    Returns:
        None.
    """

    boton_ok = page.locator("button.swal2-confirm.swal2-styled:has-text('OK')")
    try:
        if boton_ok.is_visible():
            human_delay(config, "Cerrando popup de avisos")
            boton_ok.click()
    except Exception:
        return


def main() -> None:
    """Ejecuta el pipeline completo Peritoline -> JSONL -> Generali -> ePAC.

    Returns:
        None.
    """

    setup_logging()
    logger_allianz = get_logger(tarea="peritoline_allianz")
    logger_ama = get_logger(tarea="peritoline_ama")
    logger_generali = get_logger(tarea="peritoline_generali")
    logger_pipeline = get_logger(tarea="pipeline_completo")
    parser = argparse.ArgumentParser(
        description=(
            "Descarga Peritoline, genera JSONL y ejecuta notas en Generali y ePAC."
        )
    )
    parser.add_argument(
        "--modelo",
        required=True,
        help="Codigo de modelo de nota a usar (ej: 241).",
    )
    parser.add_argument(
        "--perito",
        default="",
        help="Nombre del perito a filtrar. Si se omite, incluye todos.",
    )
    parser.add_argument(
        "--peritos",
        default="",
        help="Lista de peritos separados por coma para filtrar aseguradoras.",
    )
    parser.add_argument(
        "--output-jsonl",
        default="data/notas_allianz.jsonl",
        help="Ruta de salida del JSONL de Allianz.",
    )
    parser.add_argument(
        "--output-jsonl-generali",
        default="data/notas_generali.jsonl",
        help="Ruta de salida del JSONL de Generali.",
    )
    parser.add_argument(
        "--output-jsonl-ama",
        default="data/notas_ama.jsonl",
        help="Ruta de salida del JSONL de AMA.",
    )
    parser.add_argument(
        "--skip-guardar-generali",
        action="store_true",
        help="Omite el click en GUARDAR en Generali (solo pruebas).",
    )
    parser.add_argument(
        "--skip-generali",
        action="store_true",
        help="Omite descarga, JSONL y ejecucion de Generali.",
    )
    args = parser.parse_args()

    config = load_config()
    config.keep_browser_open = False

    if not config.peritoline_login_url:
        raise SystemExit("Falta PERITOLINE_LOGIN_URL en .env")
    if not config.peritoline_username or not config.peritoline_password:
        raise SystemExit("Faltan PERITOLINE_USERNAME/PERITOLINE_PASSWORD en .env")

    allianz_output, allianz_latest, allianz_previous = _prepare_paths("allianz")
    generali_output, generali_latest, generali_previous = _prepare_paths("generali")
    ama_output, ama_latest, ama_previous = _prepare_paths("ama")

    notas_allianz: list[dict] = []
    notas_ama: list[dict] = []
    notas_generali: list[dict] = []
    pending_allianz_path = Path("data/pending_allianz.jsonl")
    pending_generali_path = Path("data/pending_generali.jsonl")
    pending_ama_path = Path("data/pending_ama.jsonl")

    logger_pipeline.info("Iniciando descarga y generacion de JSONL")
    with launch_browser(config) as (context, page):
        human_delay(config, "Preparando sesion Peritoline")
        login_page = PeritolineLoginPage(page)
        login_page.open(config.peritoline_login_url)
        human_delay(config, "Login Peritoline")
        login_page.login(config.peritoline_username, config.peritoline_password)
        human_delay(config, "Esperando post-login")
        _cerrar_popup_avisos_si_existe(page, config)

        try:
            download_report_in_session(
                page,
                config,
                allianz_output,
                "ALLIANZ",
                click_view_all_button=True,
                click_view_all_list=True,
            )
            logger_allianz.info("Reporte Allianz descargado en: %s", allianz_output)
            shutil.copy2(allianz_output, allianz_latest)
            _prune_old_reports(Path("data/peritoline/raw_allianz"), keep=3)

            current_allianz = parse_report(allianz_output)
            previous_allianz = (
                parse_report(allianz_previous) if allianz_previous else []
            )
            cambios_allianz = compute_contact_changes(current_allianz, previous_allianz)
            peritos = set(_parse_peritos(args.peritos))
            if args.perito:
                peritos.add(normalize_text(args.perito))
            if peritos:
                filtrados_allianz = [
                    row
                    for row in cambios_allianz
                    if _match_perito(row.get("perito", ""), peritos)
                ]
            else:
                filtrados_allianz = list(cambios_allianz)

            notas_allianz = []
            for row in filtrados_allianz:
                codigo = row["codigo"]
                notas_allianz.append(
                    {
                        "codigo": codigo,
                        "modelo": args.modelo,
                        "texto": _build_text_allianz(row.get("visita", "")),
                    }
                )
                if row.get("cambio_visita"):
                    motivo = "visita actualizada"
                elif row.get("cambio_contacto"):
                    motivo = "contacto nuevo"
                else:
                    motivo = "cambio detectado"
                logger_allianz.info("Siniestro listo para ePAC (%s): %s", motivo, codigo)
        except Exception:
            logger_allianz.exception("Fallo la descarga o parseo de Allianz")

        if args.skip_generali:
            logger_generali.info("Generali omitido por configuracion")
        else:
            try:
                download_report_in_session(
                    page,
                    config,
                    generali_output,
                    "GENERALI",
                    click_view_all_button=False,
                    click_view_all_list=True,
                )
                logger_generali.info(
                    "Reporte Generali descargado en: %s", generali_output
                )
                shutil.copy2(generali_output, generali_latest)
                _prune_old_reports(Path("data/peritoline/raw_generali"), keep=3)

                current_generali = parse_report(generali_output)
                previous_generali = (
                    parse_report(generali_previous) if generali_previous else []
                )
                cambios_generali = compute_contact_changes(
                    current_generali, previous_generali
                )
                peritos = set(_parse_peritos(args.peritos))
                if args.perito:
                    peritos.add(normalize_text(args.perito))
                if peritos:
                    cambios_generali = [
                        row
                        for row in cambios_generali
                        if _match_perito(row.get("perito", ""), peritos)
                    ]
                notas_generali = []
                for row in cambios_generali:
                    codigo = row["codigo"]
                    notas_generali.append(
                        {
                            "codigo": codigo,
                            "fecha_visita": row.get("visita", ""),
                            "texto": _build_text_generali(row.get("visita", "")),
                        }
                    )
                    if row.get("cambio_visita"):
                        motivo = "visita actualizada"
                    elif row.get("cambio_contacto"):
                        motivo = "contacto nuevo"
                    else:
                        motivo = "cambio detectado"
                    logger_generali.info(
                        "Siniestro listo para Generali (%s): %s", motivo, codigo
                    )
            except Exception:
                logger_generali.exception("Fallo la descarga o parseo de Generali")

        try:
            download_report_in_session(
                page,
                config,
                ama_output,
                "AMA",
                click_view_all_button=False,
                click_view_all_list=True,
            )
            logger_ama.info("Reporte AMA descargado en: %s", ama_output)
            shutil.copy2(ama_output, ama_latest)
            _prune_old_reports(Path("data/peritoline/raw_ama"), keep=3)

            current_ama = parse_report(ama_output)
            previous_ama = parse_report(ama_previous) if ama_previous else []
            cambios_ama = compute_contact_changes(current_ama, previous_ama)
            peritos = set(_parse_peritos(args.peritos))
            if args.perito:
                peritos.add(normalize_text(args.perito))
            if peritos:
                cambios_ama = [
                    row
                    for row in cambios_ama
                    if _match_perito(row.get("perito", ""), peritos)
                ]
            notas_ama = []
            for row in cambios_ama:
                codigo = row["codigo"]
                visita = row.get("visita", "")
                notas_ama.append(
                    {
                        "codigo": codigo,
                        "fecha_visita": visita,
                        "texto": _build_text_ama(visita),
                    }
                )
                if row.get("cambio_visita"):
                    motivo = "visita actualizada"
                elif row.get("cambio_contacto"):
                    motivo = "contacto nuevo"
                else:
                    motivo = "cambio detectado"
                logger_ama.info("Siniestro listo para AMA (%s): %s", motivo, codigo)
        except Exception:
            logger_ama.exception("Fallo la descarga o parseo de AMA")

        output_jsonl = Path(args.output_jsonl)
        build_jsonl(notas_allianz, output_jsonl)
        logger_allianz.info(
            "Notas Allianz generadas: %s (%s entradas)",
            output_jsonl,
            len(notas_allianz),
        )

        if not args.skip_generali:
            output_jsonl_generali = Path(args.output_jsonl_generali)
            build_jsonl(notas_generali, output_jsonl_generali)
            logger_generali.info(
                "Notas Generali generadas: %s (%s entradas)",
                output_jsonl_generali,
                len(notas_generali),
            )

        output_jsonl_ama = Path(args.output_jsonl_ama)
        build_jsonl(notas_ama, output_jsonl_ama)
        logger_ama.info(
            "Notas AMA generadas: %s (%s entradas)",
            output_jsonl_ama,
            len(notas_ama),
        )

        pending_allianz = _merge_and_persist_pending(
            pending_allianz_path, notas_allianz, ("codigo",)
        )
        if args.skip_generali:
            pending_generali = []
        else:
            pending_generali = _merge_and_persist_pending(
                pending_generali_path, notas_generali, ("codigo",)
            )
        pending_ama = _merge_and_persist_pending(
            pending_ama_path, notas_ama, ("codigo",)
        )

        credenciales_epac = {}
        credenciales_ama = {}

        if pending_generali:
            logger_generali.info(
                "Iniciando notas Generali (%s entradas)", len(pending_generali)
            )
            try:
                run_generali_with_page(
                    page,
                    config,
                    pending_generali,
                    skip_guardar=args.skip_guardar_generali,
                )
                logger_generali.info("Notas Generali completadas")
                pending_generali_path.unlink(missing_ok=True)
            except Exception:
                logger_generali.exception(
                    "Fallo en Generali; se continua con el flujo."
                )
                _volver_a_peritoline(page, config, logger_generali)
        else:
            logger_generali.info("No hay notas nuevas de Generali para procesar.")

        ama_page = None
        if pending_ama:
            try:
                navigation = PeritolineNavigationPage(page, config)
                if navigation.abrir_aseguradoras():
                    logger_ama.info("Acceso a Aseguradoras completado")
                    navigation.abrir_editar_aseguradora("AMA")
                    logger_ama.info("Edicion de AMA abierta")
                    navigation.abrir_tab_claves()
                    logger_ama.info("Pestana Claves abierta")
                    credenciales_ama = navigation.obtener_credenciales_epac()
                    if credenciales_ama.get("username") and credenciales_ama.get("password"):
                        config.username = credenciales_ama["username"]
                        config.password = credenciales_ama["password"]
                        logger_ama.info("Credenciales AMA actualizadas desde Peritoline")
                    if credenciales_ama.get("url"):
                        config.base_url = credenciales_ama["url"]
                        logger_ama.info("URL AMA actualizada desde Peritoline")
                    ama_page = navigation.abrir_epac_desde_claves()
                    logger_ama.info("Pestana AMA abierta desde Claves")
                else:
                    logger_ama.warning("No se pudo abrir Aseguradoras para AMA")
            except Exception:
                logger_ama.exception(
                    "Fallo al preparar credenciales o abrir AMA; se omite AMA."
                )
                _volver_a_peritoline(page, config, logger_ama)

        if pending_ama and ama_page:
            logger_ama.info("Iniciando ejecucion de notas AMA")
            try:
                run_ama_with_page(ama_page, config, pending_ama)
                logger_ama.info("Ejecucion de notas AMA finalizada")
                pending_ama_path.unlink(missing_ok=True)
            except Exception:
                logger_ama.exception("Fallo al ejecutar AMA; se continua el flujo.")
                _volver_a_peritoline(page, config, logger_ama)
        elif pending_ama:
            logger_ama.info("No se pudo abrir AMA desde Peritoline")

        epac_page = None
        if pending_allianz:
            try:
                navigation = PeritolineNavigationPage(page, config)
                if navigation.abrir_aseguradoras():
                    logger_allianz.info("Acceso a Aseguradoras completado")
                    navigation.abrir_editar_aseguradora("ALLIANZ")
                    logger_allianz.info("Edicion de ALLIANZ abierta")
                    navigation.abrir_tab_claves()
                    logger_allianz.info("Pestana Claves abierta")
                    credenciales_epac = navigation.obtener_credenciales_epac()
                    if credenciales_epac.get("username") and credenciales_epac.get("password"):
                        config.username = credenciales_epac["username"]
                        config.password = credenciales_epac["password"]
                        logger_allianz.info("Credenciales ePAC actualizadas desde Peritoline")
                    if credenciales_epac.get("url"):
                        config.base_url = credenciales_epac["url"]
                        logger_allianz.info("URL ePAC actualizada desde Peritoline")
                    epac_page = navigation.abrir_epac_desde_claves()
                    logger_allianz.info("Pestana ePAC abierta desde Claves")
                else:
                    logger_allianz.warning("No se pudo abrir Aseguradoras")
            except Exception:
                logger_allianz.exception(
                    "Fallo al preparar credenciales o abrir ePAC; se omite ePAC."
                )
                _volver_a_peritoline(page, config, logger_allianz)

        if pending_allianz and epac_page:
            logger_epac = get_logger(tarea="epac_notas")
            logger_epac.info("Iniciando ejecucion de notas ePAC")
            try:
                run_workflow_with_page(context, epac_page, config, pending_allianz)
                logger_epac.info("Ejecucion de notas ePAC finalizada")
                pending_allianz_path.unlink(missing_ok=True)
            except Exception:
                logger_epac.exception("Fallo al ejecutar ePAC; flujo finalizado.")
                _volver_a_peritoline(page, config, logger_epac)
        elif pending_allianz:
            logger_allianz.info("No se pudo abrir ePAC desde Peritoline")
        else:
            logger_allianz.info("No hay notas nuevas de Allianz para procesar.")
            logger_pipeline.info("Pipeline finalizado sin ejecucion de ePAC")
            return

    logger_pipeline.info("Pipeline finalizado")


if __name__ == "__main__":
    main()
