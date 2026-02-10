"""Prueba de navegacion en Generali con un siniestro fijo."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from browser import launch_browser  # noqa: E402
from config import load_config  # noqa: E402
from generali.navigation_page import GeneraliNavigationPage  # noqa: E402
from peritoline.login_page import PeritolineLoginPage  # noqa: E402
from playwright.sync_api import Page  # noqa: E402
from utils.human import human_delay  # noqa: E402
from utils.logging_utils import get_logger, setup_logging  # noqa: E402


def _cerrar_popup_avisos_si_existe(page: Page) -> None:
    """Cierra el popup de avisos si aparece tras el login.

    Args:
        page: Pagina activa.

    Returns:
        None.
    """

    boton_ok = page.locator("button.swal2-confirm.swal2-styled:has-text('OK')")
    try:
        if boton_ok.is_visible():
            boton_ok.click()
    except Exception:
        return


def main() -> None:
    """Ejecuta el flujo hasta el filtrado del siniestro en Generali."""

    setup_logging()
    config = load_config()
    siniestro = "G2425336001302"
    fecha_visita = "05/01/2026"
    texto_sin_visita = "Contacto con el asegurado realizado."
    texto_con_visita = f"Intervencion fijada para la fecha {fecha_visita}."
    do_guardar = False
    logger = get_logger(siniestro=siniestro, tarea="generali_test")

    if not config.peritoline_login_url:
        raise SystemExit("Falta PERITOLINE_LOGIN_URL en .env")
    if not config.peritoline_username or not config.peritoline_password:
        raise SystemExit("Faltan PERITOLINE_USERNAME/PERITOLINE_PASSWORD en .env")

    with launch_browser(config) as (_, page):
        human_delay(config, "Preparando sesion Peritoline", siniestro=siniestro)
        login_page = PeritolineLoginPage(page)
        login_page.open(config.peritoline_login_url)
        human_delay(config, "Login Peritoline", siniestro=siniestro)
        login_page.login(config.peritoline_username, config.peritoline_password)
        human_delay(config, "Esperando post-login", siniestro=siniestro)
        _cerrar_popup_avisos_si_existe(page)

        navigation = GeneraliNavigationPage(page, config=config)
        generali_page = navigation.abrir_generali_desde_peritoline()
        human_delay(config, "Abriendo Generali", siniestro=siniestro)

        navigation = GeneraliNavigationPage(generali_page, config=config)
        navigation.abrir_plataforma_web()
        human_delay(config, "Accediendo a Plataforma Web", siniestro=siniestro)
        navigation.click_ver_todos()
        human_delay(config, "Aplicando Ver Todos", siniestro=siniestro)
        navigation.filtrar_por_siniestro(siniestro)
        logger.info("Filtro de siniestro ejecutado")
        navigation.abrir_siniestro(siniestro)
        logger.info("Siniestro abierto")
        navigation.informar_situacion(siniestro)
        logger.info("Seccion informar situacion abierta")
        navigation.seleccionar_codigo_situacion(siniestro, fecha_visita)
        logger.info("Codigo de situacion seleccionado")
        if fecha_visita:
            navigation.completar_observaciones(siniestro, texto_con_visita)
            logger.info("Observaciones completadas")
            navigation.completar_fecha_gestion(siniestro, fecha_visita)
            logger.info("Fecha de gestion completada")
        else:
            navigation.completar_observaciones(siniestro, texto_sin_visita)
            logger.info("Observaciones completadas")
        if do_guardar:
            navigation.guardar_situacion(siniestro)
            logger.info("Situacion guardada")
            navigation.volver_a_plataforma_web(siniestro)
            logger.info("Retorno a Plataforma Web completado")
        input("Generali test finalizado. Presiona Enter para cerrar el navegador...")


if __name__ == "__main__":
    main()
