"""Runner simple para validar login + descarga en Peritoline."""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from browser import launch_browser  # noqa: E402
from config import load_config  # noqa: E402
from peritoline.downloader import download_report  # noqa: E402
from utils.human import human_delay  # noqa: E402
from utils.logging_utils import get_logger, setup_logging  # noqa: E402


def _prune_old_reports(base_dir: Path, keep: int = 3) -> None:
    """Mantiene solo los ultimos N reportes con timestamp.

    Args:
        base_dir: Carpeta donde se guardan los reportes.
        keep: Numero de reportes a conservar.

    Returns:
        None.
    """

    reports = sorted(base_dir.glob("peritoline_report_*.xlsx"), reverse=True)
    for path in reports[keep:]:
        path.unlink(missing_ok=True)


def main() -> None:
    """Ejecuta el runner de descarga de Peritoline.

    Returns:
        None.
    """

    setup_logging()
    config = load_config()
    logger = get_logger(tarea="peritoline_allianz")

    if not config.peritoline_login_url:
        raise SystemExit("Falta PERITOLINE_LOGIN_URL en .env")
    if not config.peritoline_username or not config.peritoline_password:
        raise SystemExit("Faltan PERITOLINE_USERNAME/PERITOLINE_PASSWORD en .env")

    base_dir = Path("data/peritoline/raw")
    base_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = base_dir / f"peritoline_report_{timestamp}.xlsx"
    latest_path = base_dir / "peritoline_report_latest.xlsx"
    previous_path = base_dir / "peritoline_report_previous.xlsx"

    if latest_path.exists():
        shutil.copy2(latest_path, previous_path)

    with launch_browser(config) as (_, page):
        human_delay(config, "Preparando sesion Peritoline")
        download_report(
            page=page,
            config=config,
            login_url=config.peritoline_login_url,
            output_path=output_path,
            username=config.peritoline_username,
            password=config.peritoline_password,
        )

    shutil.copy2(output_path, latest_path)
    _prune_old_reports(base_dir, keep=3)

    logger.info("Reporte descargado en: %s", output_path)
    logger.info("Reporte actual (alias): %s", latest_path)
    if previous_path.exists():
        logger.info("Reporte anterior: %s", previous_path)


if __name__ == "__main__":
    main()
