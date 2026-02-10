"""Runner para ejecutar notas ePAC desde Peritoline y Claves."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from browser import launch_browser  # noqa: E402
from config import AppConfig, load_config  # noqa: E402
from epac.workflow import run_workflow_with_page  # noqa: E402
from peritoline.login_page import PeritolineLoginPage  # noqa: E402
from peritoline.navigation_page import PeritolineNavigationPage  # noqa: E402
from utils.human import human_delay  # noqa: E402
from utils.logging_utils import get_logger, setup_logging  # noqa: E402


def _load_notas_epac(path: Path) -> List[Dict[str, str]]:
    """Lee el archivo JSONL de ePAC.

    Args:
        path: Ruta al JSONL.

    Returns:
        Lista de notas con codigo, modelo y texto.
    """

    notas: List[Dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig") as fh:
        for line_number, line in enumerate(fh, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Linea {line_number}: JSON invalido ({exc})") from exc

            for key in ("codigo", "modelo", "texto"):
                if key not in payload or not payload[key]:
                    raise ValueError(
                        f"Linea {line_number}: falta el campo obligatorio '{key}'."
                    )

            notas.append(payload)

    if not notas:
        raise ValueError("El archivo JSONL no contiene ninguna nota valida.")
    return notas


def _cerrar_popup_avisos_si_existe(page, config: AppConfig) -> None:
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
    """Ejecuta notas ePAC leyendo credenciales desde Peritoline.

    Returns:
        None.
    """

    setup_logging()
    logger = get_logger(tarea="epac_notas")
    parser = argparse.ArgumentParser(
        description="Ejecuta notas ePAC desde Peritoline y Claves."
    )
    parser.add_argument(
        "--notas-jsonl",
        default="data/notas_allianz.jsonl",
        help="Ruta al JSONL de ePAC (Allianz).",
    )
    args = parser.parse_args()

    notas = _load_notas_epac(Path(args.notas_jsonl))
    config = load_config()
    config.keep_browser_open = False

    if not config.peritoline_login_url:
        raise SystemExit("Falta PERITOLINE_LOGIN_URL en .env")
    if not config.peritoline_username or not config.peritoline_password:
        raise SystemExit("Faltan PERITOLINE_USERNAME/PERITOLINE_PASSWORD en .env")

    with launch_browser(config) as (context, page):
        human_delay(config, "Preparando sesion Peritoline")
        login_page = PeritolineLoginPage(page)
        login_page.open(config.peritoline_login_url)
        human_delay(config, "Login Peritoline")
        login_page.login(config.peritoline_username, config.peritoline_password)
        human_delay(config, "Esperando post-login")
        _cerrar_popup_avisos_si_existe(page, config)

        navigation = PeritolineNavigationPage(page, config)
        if not navigation.abrir_aseguradoras():
            raise RuntimeError("No se pudo abrir Aseguradoras en Peritoline.")

        navigation.abrir_editar_aseguradora("ALLIANZ")
        human_delay(config, "Edicion de ALLIANZ abierta")
        navigation.abrir_tab_claves()
        human_delay(config, "Pestana Claves abierta")

        credenciales = navigation.obtener_credenciales_epac()
        if credenciales.get("username") and credenciales.get("password"):
            config.username = credenciales["username"]
            config.password = credenciales["password"]
        if credenciales.get("url"):
            config.base_url = credenciales["url"]

        epac_page = navigation.abrir_epac_desde_claves()
        logger.info("Pestana ePAC abierta desde Claves")
        run_workflow_with_page(context, epac_page, config, notas)
        logger.info("Notas ePAC finalizadas")


if __name__ == "__main__":
    main()
