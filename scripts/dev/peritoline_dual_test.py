"""Descarga Excel de Allianz y Generali en una sola sesion."""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from browser import launch_browser  # noqa: E402
from config import load_config  # noqa: E402
from peritoline.downloader import download_report_in_session  # noqa: E402
from peritoline.login_page import PeritolineLoginPage  # noqa: E402
from pipeline.build_notas import build_jsonl  # noqa: E402
from processing.diff import compute_contact_changes  # noqa: E402
from processing.excel_parser import normalize_text, parse_report  # noqa: E402
from utils.human import human_delay  # noqa: E402
from utils.logging_utils import get_logger, setup_logging  # noqa: E402


def _prepare_paths(prefix: str) -> tuple[Path, Path, Path]:
    """Prepara rutas para reportes con prefijo.

    Args:
        prefix: Prefijo del archivo (allianz o generali).

    Returns:
        Tupla con (output, latest, previous).
    """

    base_dir = Path(f"data/peritoline/raw_{prefix}")
    base_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = base_dir / f"{prefix}_report_{timestamp}.xlsx"
    latest_path = base_dir / f"{prefix}_report_latest.xlsx"
    previous_path = base_dir / f"{prefix}_report_previous.xlsx"
    if latest_path.exists():
        shutil.copy2(latest_path, previous_path)
    return output_path, latest_path, previous_path


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


def main() -> None:
    """Ejecuta la descarga de Allianz y Generali en una sola sesion.

    Returns:
        None.
    """

    setup_logging()
    config = load_config()
    logger = get_logger(tarea="peritoline_dual")
    logger_allianz = get_logger(tarea="peritoline_allianz")
    logger_generali = get_logger(tarea="peritoline_generali")

    if not config.peritoline_login_url:
        raise SystemExit("Falta PERITOLINE_LOGIN_URL en .env")
    if not config.peritoline_username or not config.peritoline_password:
        raise SystemExit("Faltan PERITOLINE_USERNAME/PERITOLINE_PASSWORD en .env")

    allianz_output, allianz_latest, allianz_previous = _prepare_paths("allianz")
    generali_output, generali_latest, _ = _prepare_paths("generali")

    with launch_browser(config) as (_, page):
        human_delay(config, "Preparando sesion Peritoline")
        login_page = PeritolineLoginPage(page)
        login_page.open(config.peritoline_login_url)
        human_delay(config, "Login Peritoline")
        login_page.login(config.peritoline_username, config.peritoline_password)
        human_delay(config, "Esperando post-login")

        download_report_in_session(
            page,
            config,
            allianz_output,
            "ALLIANZ",
            click_view_all_button=True,
            click_view_all_list=True,
        )
        shutil.copy2(allianz_output, allianz_latest)

        current = parse_report(allianz_output)
        previous = parse_report(allianz_previous) if allianz_previous.exists() else []
        cambios = compute_contact_changes(current, previous)
        filtrados = cambios
        notas_allianz = [
            {
                "codigo": row["codigo"],
                "modelo": "241",
                "texto": (
                    f"Se ha concertado intervencion para fecha {row.get('visita', '')}"
                    if row.get("visita")
                    else "Se ha contactado con el asegurado"
                ),
            }
            for row in filtrados
        ]
        build_jsonl(notas_allianz, Path("data/notas_allianz.jsonl"))

        download_report_in_session(
            page,
            config,
            generali_output,
            "GENERALI",
            click_view_all_button=False,
            click_view_all_list=True,
        )

    shutil.copy2(generali_output, generali_latest)
    _prune_old_reports(Path("data/peritoline/raw_allianz"), keep=3)
    _prune_old_reports(Path("data/peritoline/raw_generali"), keep=3)

    logger_allianz.info("Reporte Allianz descargado en: %s", allianz_output)
    logger_allianz.info(
        "Notas Allianz generadas en: %s", Path("data/notas_allianz.jsonl")
    )
    logger_generali.info("Reporte Generali descargado en: %s", generali_output)


if __name__ == "__main__":
    main()
