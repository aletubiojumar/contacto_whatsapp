"""Orquestacion principal para automatizar la carga de notas en el portal."""

from __future__ import annotations

import time
from typing import Any, Iterable, Dict

from playwright.sync_api import BrowserContext, FrameLocator, Page, TimeoutError

from config import AppConfig
from browser import launch_browser
from epac.pages.login_page import LoginPage
from epac.pages.navigation_page import NavigationPage
from epac.pages.num_siniestro_page import NumeroSiniestroPage
from epac.pages.menu_lateral_page import MenuLateralPage
from epac.pages.nota_tab_page import NotaTabPage
from epac.pages.popup_modelo_page import PopupModeloPage
from utils.human import human_delay
from utils.logging_utils import get_logger


def run_workflow(config: AppConfig, codigo: str, modelo: str, texto: str) -> Any:
    """Ejecuta el flujo completo para un solo siniestro.

    Args:
        config: Configuracion de la aplicacion.
        codigo: Codigo del siniestro.
        modelo: Codigo del modelo de nota.
        texto: Texto a registrar en la nota.

    Returns:
        Resultado del flujo (None en el flujo actual).
    """

    notas = [{"codigo": codigo, "modelo": modelo, "texto": texto}]
    return run_workflow_in_session(config, notas)


def run_workflow_in_session(config: AppConfig, notas: Iterable[Dict[str, str]]) -> Any:
    """Ejecuta el flujo completo reutilizando la misma sesion.

    - Login una sola vez.
    - Por cada nota, vuelve a "Informe Pericial Diversos SEA".

    Args:
        config: Configuracion de la aplicacion.
        notas: Iterable de notas con codigo, modelo y texto.

    Returns:
        Resultado del flujo (None en el flujo actual).
    """

    with launch_browser(config) as (context, page):
        _login_epac(page, config)
        main_page = page

        for nota in notas:
            codigo = nota["codigo"]
            modelo = nota["modelo"]
            texto = nota["texto"]
            logger = get_logger(siniestro=codigo, tarea="inicio")
            logger.info("Iniciando procesamiento del siniestro")

            _ir_a_informe_pericial_con_reintentos(
                context, main_page, config, codigo=codigo
            )
            main_page = _procesar_nota(context, main_page, config, codigo, modelo, texto)
            logger_final = get_logger(siniestro=codigo, tarea="epac_notas")
            logger_final.info("Siniestro finalizado en ePAC")

        return None


def run_workflow_with_page(
    context: BrowserContext,
    page: Page,
    config: AppConfig,
    notas: Iterable[Dict[str, str]],
) -> Any:
    """Ejecuta el flujo completo usando una pestana ya abierta en ePAC.

    Notas:
        Documentacion pensada para MkDocs.

    Args:
        context: Contexto del navegador.
        page: Pagina activa de ePAC.
        config: Configuracion de la aplicacion.
        notas: Iterable de notas con codigo, modelo y texto.

    Returns:
        Resultado del flujo (None en el flujo actual).
    """

    _login_epac(page, config)
    main_page = page

    for nota in notas:
        codigo = nota["codigo"]
        modelo = nota["modelo"]
        texto = nota["texto"]
        logger = get_logger(siniestro=codigo, tarea="inicio")
        logger.info("Iniciando procesamiento del siniestro")

        _ir_a_informe_pericial_con_reintentos(
            context, main_page, config, codigo=codigo
        )
        main_page = _procesar_nota(context, main_page, config, codigo, modelo, texto)
        logger_final = get_logger(siniestro=codigo, tarea="epac_notas")
        logger_final.info("Siniestro finalizado en ePAC")

    return None


def _login_epac(page: Page, config: AppConfig) -> None:
    """Inicia sesion en ePAC.

    Args:
        page: Pagina principal de Playwright.
        config: Configuracion con credenciales y URL base.

    Returns:
        None.
    """

    login_page = LoginPage(page)
    login_page.open(config.base_url)
    human_delay(config, "Revisando pantalla de login")
    login_page.login(config.username, config.password)
    human_delay(config, "Esperando respuesta tras login")
    _validar_login_epac(page)


def _validar_login_epac(page: Page) -> None:
    """Valida si el login de ePAC fue exitoso.

    Notas:
        Documentacion pensada para MkDocs.

    Args:
        page: Pagina principal de Playwright.

    Returns:
        None.
    """

    aplic_allianz_link = page.get_by_role(
        "menuitem", name="Aplic. Allianz", exact=True
    )
    try:
        aplic_allianz_link.wait_for(state="visible", timeout=15_000)
    except TimeoutError as exc:
        logger = get_logger(tarea="epac_login")
        logger.error("Login ePAC no exitoso; se omite ePAC")
        raise RuntimeError("Login ePAC no exitoso") from exc


def _ir_a_informe_pericial(
    page: Page, config: AppConfig, siniestro: str = "sin_codigo"
) -> None:
    """Navega al menu Aplic. Allianz -> Informe Pericial Diversos SEA.

    Args:
        page: Pagina activa.
        config: Configuracion de la aplicacion.
        siniestro: Codigo de siniestro para trazabilidad.

    Returns:
        None.
    """

    navigation = NavigationPage(page, config)
    navigation.goto_informe_pericial_diversos_sea()
    human_delay(config, "Leyendo submenu seleccionado", siniestro=siniestro)


def _ir_a_informe_pericial_con_reintentos(
    context: BrowserContext,
    page: Page,
    config: AppConfig,
    codigo: str = "sin_codigo",
    intentos: int = 10,
) -> None:
    """Reintenta la navegacion si no aparecen los campos del siniestro.

    Args:
        context: Contexto del navegador.
        page: Pagina activa.
        config: Configuracion de la aplicacion.
        codigo: Codigo del siniestro.
        intentos: Numero de reintentos.

    Returns:
        None.
    """

    for intento in range(1, intentos + 1):
        _ir_a_informe_pericial(page, config, siniestro=codigo)
        try:
            _resolve_scope_for_selector(
                NumeroSiniestroPage.SINIESTRO_INPUT, context, page, siniestro=codigo
            )
            return
        except RuntimeError:
            logger = get_logger(siniestro=codigo, tarea="reintento_menu")
            logger.warning(
                "No se detecto el formulario tras navegar; reintentando menu (%s/%s).",
                intento,
                intentos,
            )
            human_delay(config, "Reintentando menu Aplic. Allianz", siniestro=codigo)
            time.sleep(1)
            continue

    raise RuntimeError(
        "No se pudo abrir el formulario de siniestro tras varios reintentos."
    )


def _procesar_nota(
    context: BrowserContext,
    page: Page,
    config: AppConfig,
    codigo: str,
    modelo: str,
    texto: str,
) -> Page:
    """Procesa una nota y devuelve la pagina principal para continuar.

    Args:
        context: Contexto del navegador.
        page: Pagina activa.
        config: Configuracion de la aplicacion.
        codigo: Codigo del siniestro.
        modelo: Codigo del modelo de nota.
        texto: Texto a registrar.

    Returns:
        Pagina principal para continuar el flujo.
    """

    scope = _resolve_scope_for_selector(
        NumeroSiniestroPage.SINIESTRO_INPUT, context, page, siniestro=codigo
    )

    siniestro_page = NumeroSiniestroPage(scope)
    siniestro_page.wait_until_ready()
    human_delay(config, "Preparando campo 'Siniestro / Encargo'", siniestro=codigo)
    siniestro_page.fill_siniestro_number(codigo)
    human_delay(config, "Codigo ingresado; listo para los siguientes pasos", siniestro=codigo)
    siniestro_page.submit_codigo()
    human_delay(config, "Codigo enviado, esperando siguiente vista", siniestro=codigo)
    siniestro_page.seleccionar_resultado_por_codigo(codigo)
    human_delay(
        config,
        "Resultado seleccionado; continuar con la siguiente pantalla",
        siniestro=codigo,
    )
    menu_scope = _resolve_scope_for_selector(
        MenuLateralPage.FICHA_GESTION_BUTTON, context, page, siniestro=codigo
    )
    menu_page = MenuLateralPage(menu_scope)
    menu_page.abrir_ficha_gestion()
    human_delay(config, "Abriendo 'Ficha Gestion'", siniestro=codigo)
    page = _wait_for_new_page(context, page, siniestro=codigo)
    _wait_for_selector_with_retry(page, NotaTabPage.NOTA_LINK)

    nota_page = NotaTabPage(page)
    nota_page.abrir_seccion_nota()
    human_delay(config, "Ingresando en la seccion 'Nota'", siniestro=codigo)
    popup = _abrir_popup_modelo(context, nota_page, siniestro=codigo)
    popup.seleccionar_modelo(modelo)
    _wait_for_selector_with_retry(page, nota_page.CONTENIDO_TEXTAREA)
    nota_page.rellenar_texto(texto)
    nota_page.grabar_nota()
    human_delay(
        config, "Nota grabada; continuando con la siguiente entrada", siniestro=codigo
    )
    time.sleep(2)
    return _cerrar_y_volver_a_menu(context, page, config, siniestro=codigo)


def _resolve_scope_for_selector(
    selector: str,
    context: BrowserContext,
    current_page: Page,
    siniestro: str = "sin_codigo",
) -> Page | FrameLocator:
    """Determina si el selector vive en la pagina principal o en un iframe.

    Args:
        selector: Selector CSS a buscar.
        context: Contexto del navegador.
        current_page: Pagina actual.
        siniestro: Codigo del siniestro para trazabilidad.

    Returns:
        Page o FrameLocator donde existe el selector.
    """

    page = _maybe_switch_page(context, current_page, siniestro=siniestro)
    try:
        page.wait_for_selector(selector, state="visible", timeout=5_000)
        return page
    except TimeoutError:
        pass

    iframe_locator = page.locator("iframe")
    count = iframe_locator.count()
    for idx in range(count):
        candidate = page.frame_locator("iframe").nth(idx)
        try:
            candidate.locator(selector).wait_for(state="visible", timeout=5_000)
            logger = get_logger(siniestro=siniestro, tarea="detectar_formulario")
            logger.info("Formulario detectado en iframe #%s.", idx)
            return candidate
        except TimeoutError:
            continue

    raise RuntimeError(f"No se encontro el selector '{selector}' en la pagina.")


def _maybe_switch_page(
    context: BrowserContext, current_page: Page, siniestro: str = "sin_codigo"
) -> Page:
    """Cambia el foco si el portal abrio una pestana nueva para el formulario.

    Args:
        context: Contexto del navegador.
        current_page: Pagina actual.
        siniestro: Codigo del siniestro para trazabilidad.

    Returns:
        Pagina activa tras el posible cambio.
    """

    pages = context.pages
    if pages and pages[-1] is not current_page:
        logger = get_logger(siniestro=siniestro, tarea="cambio_pestana")
        logger.info("Detectada nueva pestana para el formulario, cambiando de contexto.")
        target_page = pages[-1]
        target_page.bring_to_front()
        target_page.wait_for_load_state("domcontentloaded")
        return target_page

    return current_page


def _wait_for_new_page(
    context: BrowserContext, current_page: Page, siniestro: str = "sin_codigo"
) -> Page:
    """Detecta si 'Ficha Gestion' abrio otra pestana y devuelve la pagina activa.

    Args:
        context: Contexto del navegador.
        current_page: Pagina actual.
        siniestro: Codigo del siniestro para trazabilidad.

    Returns:
        Pagina activa tras la apertura de pestana.
    """

    pages = context.pages
    if pages and pages[-1] is not current_page:
        target_page = pages[-1]
        target_page.bring_to_front()
        target_page.wait_for_load_state("domcontentloaded")
        logger = get_logger(siniestro=siniestro, tarea="ficha_gestion")
        logger.info("Nueva pestana detectada tras abrir 'Ficha Gestion'.")
        return target_page

    logger = get_logger(siniestro=siniestro, tarea="ficha_gestion")
    logger.info("No aparecio nueva pestana; se continua con la actual.")
    current_page.wait_for_load_state("domcontentloaded")
    return current_page


def _wait_for_selector_with_retry(page: Page, selector: str, timeout: int = 15_000) -> None:
    """Aplica una espera simple para cualquier selector que tarde en renderizar.

    Args:
        page: Pagina activa.
        selector: Selector CSS.
        timeout: Tiempo maximo de espera en ms.

    Returns:
        None.
    """

    page.wait_for_selector(selector, state="visible", timeout=timeout)


def _cerrar_y_volver_a_menu(
    context: BrowserContext,
    current_page: Page,
    config: AppConfig,
    siniestro: str = "sin_codigo",
) -> Page:
    """Cierra la pestana actual y reabre el menu principal de ePAC.

    Args:
        context: Contexto del navegador.
        current_page: Pagina actual.
        config: Configuracion de la aplicacion.
        siniestro: Codigo del siniestro para trazabilidad.

    Returns:
        Pagina principal tras cerrar la pestana.
    """

    try:
        current_page.close()
    except Exception:
        pass

    remaining_pages = [p for p in context.pages if not p.is_closed()]
    if not remaining_pages:
        return current_page

    main_page = remaining_pages[0]
    main_page.bring_to_front()
    main_page.wait_for_load_state("domcontentloaded")
    _ir_a_informe_pericial(main_page, config, siniestro=siniestro)
    human_delay(
        config,
        "Reabriendo Aplic. Allianz > Informe Pericial Diversos SEA",
        siniestro=siniestro,
    )
    logger = get_logger(siniestro=siniestro, tarea="volver_menu")
    logger.info("Retorno al menu principal completado.")
    return main_page


def _abrir_popup_modelo(
    context: BrowserContext, nota_page: NotaTabPage, siniestro: str = "sin_codigo"
) -> PopupModeloPage:
    """Abre el popup de modelos de nota y devuelve su Page Object.

    Args:
        context: Contexto del navegador.
        nota_page: Page Object de la nota.
        siniestro: Codigo del siniestro para trazabilidad.

    Returns:
        Page Object del popup.
    """

    for intento in range(3):
        try:
            with context.expect_page(timeout=15_000) as popup_event:
                nota_page.abrir_busqueda_modelo()
            popup_page = popup_event.value
            popup_page.bring_to_front()
            popup_page.wait_for_load_state("domcontentloaded")
            popup = PopupModeloPage(popup_page, siniestro=siniestro)
            popup.wait_until_visible()
            return popup
        except TimeoutError:
            logger = get_logger(siniestro=siniestro, tarea="popup_modelo")
            logger.warning(
                "No se detecto el popup al intento %s; reintentando...",
                intento + 1,
            )
            time.sleep(1)

    raise TimeoutError("No se pudo abrir la ventana de modelos despues de varios intentos.")
