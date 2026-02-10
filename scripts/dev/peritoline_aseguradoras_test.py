"""Prueba de acceso a Aseguradoras desde Peritoline."""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import Page

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from browser import launch_browser  # noqa: E402
from config import load_config  # noqa: E402
from peritoline.login_page import PeritolineLoginPage  # noqa: E402
from peritoline.navigation_page import PeritolineNavigationPage  # noqa: E402
from utils.human import human_delay  # noqa: E402
from utils.logging_utils import get_logger, setup_logging  # noqa: E402


def _cerrar_popup_avisos_si_existe(page: Page, config) -> None:
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
    """Ejecuta login en Peritoline y abre Aseguradoras."""

    setup_logging()
    config = load_config()
    logger = get_logger(tarea="peritoline_aseguradoras")

    if not config.peritoline_login_url:
        raise SystemExit("Falta PERITOLINE_LOGIN_URL en .env")
    if not config.peritoline_username or not config.peritoline_password:
        raise SystemExit("Faltan PERITOLINE_USERNAME/PERITOLINE_PASSWORD en .env")

    with launch_browser(config) as (_, page):
        human_delay(config, "Preparando sesion Peritoline")
        login_page = PeritolineLoginPage(page)
        login_page.open(config.peritoline_login_url)
        human_delay(config, "Login Peritoline")
        login_page.login(config.peritoline_username, config.peritoline_password)
        human_delay(config, "Esperando post-login")
        _cerrar_popup_avisos_si_existe(page, config)

        navigation = PeritolineNavigationPage(page, config)
        if navigation.abrir_aseguradoras():
            logger.info("Acceso a Aseguradoras completado")
            navigation.abrir_editar_aseguradora("ALLIANZ")
            logger.info("Edicion de ALLIANZ abierta")
            navigation.abrir_tab_claves()
            logger.info("Pestana Claves abierta")
            credenciales = navigation.obtener_credenciales_epac()
            logger.info(
                "Credenciales ePAC detectadas: url=%s usuario=%s",
                credenciales.get("url", ""),
                credenciales.get("username", ""),
            )
        else:
            logger.warning("No se pudo abrir Aseguradoras")

        input("Peritoline test finalizado. Presiona Enter para cerrar el navegador...")


if __name__ == "__main__":
    main()
