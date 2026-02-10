"""Descarga Excel de Peritoline y genera JSONL sin ejecutar portales."""

from __future__ import annotations

import argparse
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
from pipeline.build_notas import build_jsonl  # noqa: E402
from processing.diff import compute_contact_changes  # noqa: E402
from processing.excel_parser import normalize_text, parse_report  # noqa: E402
from utils.human import human_delay  # noqa: E402
from utils.logging_utils import get_logger, setup_logging  # noqa: E402
from playwright.sync_api import Page  # noqa: E402


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


def _prepare_paths(prefix: str, logger) -> tuple[Path, Path, Path | None]:
    """Prepara rutas de salida y copia el ultimo reporte como anterior.

    Args:
        prefix: Prefijo del reporte (allianz, generali o ama).

    Returns:
        Ruta del nuevo reporte, ruta del ultimo reporte y ruta del anterior (si existe).
    """

    base_dir = Path(f"data/peritoline/raw_{prefix}")
    base_dir.mkdir(parents=True, exist_ok=True)

    latest_path = base_dir / f"{prefix}_report_latest.xlsx"
    previous_path = base_dir / f"{prefix}_report_previous.xlsx"
    if latest_path.exists():
        try:
            shutil.copy2(latest_path, previous_path)
        except PermissionError:
            if logger:
                logger.warning(
                    "No se pudo copiar %s a previous (archivo en uso).",
                    latest_path,
                )
            previous_path = None
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
    """Descarga Excel y genera JSONL para Allianz, Generali y AMA.

    Returns:
        None.
    """

    setup_logging()
    logger_allianz = get_logger(tarea="peritoline_allianz")
    logger_ama = get_logger(tarea="peritoline_ama")
    logger_generali = get_logger(tarea="peritoline_generali")
    parser = argparse.ArgumentParser(
        description="Descarga Excel de Peritoline y genera JSONL sin ejecutar portales."
    )
    parser.add_argument(
        "--modelo",
        required=True,
        help="Codigo de modelo de nota a usar para Allianz (ej: 241).",
    )
    parser.add_argument(
        "--perito",
        default="",
        help="Nombre del perito a filtrar en aseguradoras. Si se omite, incluye todos.",
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
    args = parser.parse_args()

    config = load_config()
    config.keep_browser_open = False

    if not config.peritoline_login_url:
        raise SystemExit("Falta PERITOLINE_LOGIN_URL en .env")
    if not config.peritoline_username or not config.peritoline_password:
        raise SystemExit("Faltan PERITOLINE_USERNAME/PERITOLINE_PASSWORD en .env")

    allianz_output, allianz_latest, allianz_previous = _prepare_paths(
        "allianz", logger_allianz
    )
    generali_output, generali_latest, generali_previous = _prepare_paths(
        "generali", logger_generali
    )
    ama_output, ama_latest, ama_previous = _prepare_paths("ama", logger_ama)
    ama_descargado = False

    with launch_browser(config) as (_, page):
        human_delay(config, "Preparando sesion Peritoline")
        login_page = PeritolineLoginPage(page)
        login_page.open(config.peritoline_login_url)
        human_delay(config, "Login Peritoline")
        login_page.login(config.peritoline_username, config.peritoline_password)
        human_delay(config, "Esperando post-login")
        _cerrar_popup_avisos_si_existe(page, config)

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

        download_report_in_session(
            page,
            config,
            generali_output,
            "GENERALI",
            click_view_all_button=False,
            click_view_all_list=True,
        )
        logger_generali.info("Reporte Generali descargado en: %s", generali_output)
        shutil.copy2(generali_output, generali_latest)
        _prune_old_reports(Path("data/peritoline/raw_generali"), keep=3)

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
            ama_descargado = True
        except Exception:
            logger_ama.exception("No se pudo descargar el reporte AMA")

    current_allianz = parse_report(allianz_output)
    previous_allianz = parse_report(allianz_previous) if allianz_previous else []
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

    notas_allianz = [
        {
            "codigo": row["codigo"],
            "modelo": args.modelo,
            "texto": _build_text_allianz(row.get("visita", "")),
        }
        for row in filtrados_allianz
    ]
    output_jsonl = Path(args.output_jsonl)
    build_jsonl(notas_allianz, output_jsonl)
    logger_allianz.info(
        "Notas Allianz generadas: %s (%s entradas)", output_jsonl, len(notas_allianz)
    )

    current_generali = parse_report(generali_output)
    previous_generali = parse_report(generali_previous) if generali_previous else []
    cambios_generali = compute_contact_changes(current_generali, previous_generali)
    peritos = set(_parse_peritos(args.peritos))
    if args.perito:
        peritos.add(normalize_text(args.perito))
    if peritos:
        cambios_generali = [
            row
            for row in cambios_generali
            if _match_perito(row.get("perito", ""), peritos)
        ]
    notas_generali = [
        {
            "codigo": row["codigo"],
            "fecha_visita": row.get("visita", ""),
            "texto": _build_text_generali(row.get("visita", "")),
        }
        for row in cambios_generali
    ]
    output_jsonl_generali = Path(args.output_jsonl_generali)
    build_jsonl(notas_generali, output_jsonl_generali)
    logger_generali.info(
        "Notas Generali generadas: %s (%s entradas)",
        output_jsonl_generali,
        len(notas_generali),
    )

    if ama_descargado:
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
        notas_ama = [
            {
                "codigo": row["codigo"],
                "fecha_visita": row.get("visita", ""),
                "texto": _build_text_ama(row.get("visita", "")),
            }
            for row in cambios_ama
        ]
        output_jsonl_ama = Path(args.output_jsonl_ama)
        build_jsonl(notas_ama, output_jsonl_ama)
        logger_ama.info(
            "Notas AMA generadas: %s (%s entradas)", output_jsonl_ama, len(notas_ama)
        )
    else:
        logger_ama.info("Se omite AMA porque no se pudo descargar el reporte.")


if __name__ == "__main__":
    main()
