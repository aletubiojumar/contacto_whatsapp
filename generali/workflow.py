"""Flujo de trabajo para generar notas en Generali."""

from __future__ import annotations

from typing import Dict, Iterable

from playwright.sync_api import Page

from browser import launch_browser
from config import AppConfig
from generali.navigation_page import GeneraliNavigationPage
from peritoline.login_page import PeritolineLoginPage
from utils.human import human_delay
from utils.logging_utils import get_logger


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


def run_generali_in_session(
    config: AppConfig,
    notas: Iterable[Dict[str, str]],
    skip_guardar: bool = False,
) -> None:
    """Ejecuta el flujo Generali reutilizando una sola sesion.

    Args:
        config: Configuracion de la aplicacion.
        notas: Iterable con codigo, fecha_visita y texto.
        skip_guardar: Evita el click en GUARDAR si es True.

    Returns:
        None.
    """

    logger = get_logger(tarea="generali_notas")
    logger.info("Iniciando flujo Generali en sesion nueva")
    with launch_browser(config) as (_, page):
        _login_peritoline(page, config)
        run_generali_with_page(page, config, notas, skip_guardar=skip_guardar)
    logger.info("Flujo Generali finalizado")


def run_generali_with_page(
    page: Page,
    config: AppConfig,
    notas: Iterable[Dict[str, str]],
    skip_guardar: bool = False,
) -> None:
    """Ejecuta el flujo Generali usando una sesion ya iniciada en Peritoline.

    Args:
        page: Pagina activa con Peritoline ya autenticada.
        config: Configuracion de la aplicacion.
        notas: Iterable con codigo, fecha_visita y texto.
        skip_guardar: Evita el click en GUARDAR si es True.

    Returns:
        None.
    """

    logger = get_logger(tarea="generali_notas")
    logger.info("Entrando a Generali desde Peritoline")
    peritoline_page = page
    generali_page = _abrir_generali(peritoline_page, config)
    _procesar_notas_generali(generali_page, config, notas, skip_guardar)
    _cerrar_generali_y_volver(peritoline_page, generali_page)
    logger.info("Procesamiento Generali completado")


def _cerrar_generali_y_volver(peritoline_page: Page, generali_page: Page) -> None:
    """Cierra la pestana de Generali y devuelve el foco a Peritoline.

    Notas:
        Documentacion pensada para MkDocs.

    Args:
        peritoline_page: Pagina original de Peritoline.
        generali_page: Pagina activa de Generali.

    Returns:
        None.
    """

    try:
        generali_page.close()
    except Exception:
        return

    try:
        peritoline_page.bring_to_front()
        peritoline_page.wait_for_load_state("domcontentloaded")
    except Exception:
        return


def _login_peritoline(page: Page, config: AppConfig) -> None:
    """Inicia sesion en Peritoline.

    Args:
        page: Pagina principal de Playwright.
        config: Configuracion con credenciales y URL base.

    Returns:
        None.
    """

    login_page = PeritolineLoginPage(page)
    login_page.open(config.peritoline_login_url)
    human_delay(config, "Login Peritoline")
    login_page.login(config.peritoline_username, config.peritoline_password)
    human_delay(config, "Esperando post-login")
    _cerrar_popup_avisos_si_existe(page)


def _abrir_generali(page: Page, config: AppConfig) -> Page:
    """Abre Generali desde la sesion de Peritoline.

    Args:
        page: Pagina principal con Peritoline.
        config: Configuracion con pausas humanas.

    Returns:
        Pagina de Generali.
    """

    navigation = GeneraliNavigationPage(page, config=config)
    generali_page = navigation.abrir_generali_desde_peritoline()
    human_delay(config, "Abriendo Generali")
    navigation = GeneraliNavigationPage(generali_page, config=config)
    navigation.abrir_plataforma_web()
    human_delay(config, "Accediendo a Plataforma Web")
    _validar_login_generali(generali_page)
    return generali_page


def _validar_login_generali(page: Page) -> None:
    """Valida si Generali cargo la plataforma web.

    Notas:
        Documentacion pensada para MkDocs.

    Args:
        page: Pagina activa de Generali.

    Returns:
        None.
    """

    try:
        page.get_by_role("button", name="Ver Todos").wait_for(
            state="visible", timeout=15_000
        )
    except Exception as exc:
        logger = get_logger(tarea="generali_login")
        logger.error("Login Generali no exitoso; se omite Generali")
        raise RuntimeError("Login Generali no exitoso") from exc


def _procesar_notas_generali(
    page: Page,
    config: AppConfig,
    notas: Iterable[Dict[str, str]],
    skip_guardar: bool,
) -> None:
    """Procesa cada nota en Generali dentro de la misma sesion.

    Args:
        page: Pagina de Generali.
        config: Configuracion con pausas humanas.
        notas: Iterable con codigo, fecha_visita y texto.
        skip_guardar: Evita el click en GUARDAR si es True.

    Returns:
        None.
    """

    navigation = GeneraliNavigationPage(page, config=config)
    for nota in notas:
        codigo = nota.get("codigo", "")
        fecha_visita = nota.get("fecha_visita", "")
        texto = nota.get("texto", "")
        logger = get_logger(siniestro=codigo, tarea="generali_notas")
        logger.info("Iniciando procesamiento de siniestro en Generali")

        navigation.click_ver_todos()
        human_delay(config, "Aplicando Ver Todos", siniestro=codigo)
        navigation.filtrar_por_siniestro(codigo)
        navigation.abrir_siniestro(codigo)
        navigation.informar_situacion(codigo)
        navigation.seleccionar_codigo_situacion(codigo, fecha_visita)
        navigation.completar_observaciones(codigo, texto)
        if fecha_visita:
            navigation.completar_fecha_gestion(codigo, fecha_visita)

        if skip_guardar:
            logger.info("GUARDAR omitido por configuracion")
            continue

        navigation.guardar_situacion(codigo)
        navigation.volver_a_plataforma_web(codigo)
        logger.info("Retorno a Plataforma Web completado")
        logger.info("Siniestro finalizado en Generali")
