"""Flujo de trabajo para gestionar notas en el portal AMA."""

from __future__ import annotations

from typing import Dict, Iterable, List

from playwright.sync_api import Locator, Page

from config import AppConfig
from utils.human import human_delay
from utils.logging_utils import get_logger


def run_ama_with_page(
    page: Page,
    config: AppConfig,
    notas: Iterable[Dict[str, str]],
) -> None:
    """Ejecuta el flujo AMA usando una pestana ya abierta.

    Notas:
        Documentacion pensada para MkDocs.

    Args:
        page: Pagina activa del portal AMA.
        config: Configuracion de la aplicacion.
        notas: Iterable de notas con codigo, modelo y texto.

    Returns:
        None.
    """

    logger = get_logger(tarea="ama_notas")
    logger.info("Iniciando login en AMA")
    _login_ama(page, config)
    logger.info("Login AMA completado")
    try:
        _abrir_informes_periciales(page, config)
        logger.info("Acceso a Informes Periciales completado")
    except Exception as exc:
        logger.error("Login AMA no exitoso; se omite AMA")
        raise RuntimeError("Login AMA no exitoso") from exc
    notas_list = list(notas)
    if notas_list:
        count = len(notas_list)
        human_delay(config, "Post-login AMA")
        logger.info("Notas AMA pendientes de implementar (%s entradas)", count)
        _buscar_siniestros(page, config, notas_list)
        _cerrar_pestana_ama(page, config)


def _cerrar_pestana_ama(page: Page, config: AppConfig) -> None:
    """Cierra la pestana de AMA tras procesar las notas.

    Notas:
        Documentacion pensada para MkDocs.

    Args:
        page: Pagina activa del portal AMA.
        config: Configuracion de la aplicacion.

    Returns:
        None.
    """

    try:
        human_delay(config, "Cerrando pestana AMA")
        page.close()
    except Exception:
        return


def _login_ama(page: Page, config: AppConfig) -> None:
    """Inicia sesion en AMA usando el formulario de login.

    Notas:
        Documentacion pensada para MkDocs.

    Args:
        page: Pagina activa del portal AMA.
        config: Configuracion de la aplicacion.

    Returns:
        None.
    """

    username_input = page.locator("#username").first
    password_input = page.locator("#password").first
    access_select = page.locator("#j_typeaccess").first
    submit_button = page.locator("#submit").first

    username_input.wait_for(state="visible", timeout=15_000)
    password_input.wait_for(state="visible", timeout=15_000)
    access_select.wait_for(state="visible", timeout=15_000)

    human_delay(config, "Preparando login AMA")
    username_input.fill(config.username)
    human_delay(config, "Usuario AMA completado")
    password_input.fill(config.password)
    human_delay(config, "Password AMA completado")
    access_select.select_option(value="EXPERT")
    human_delay(config, "Tipo acceso AMA seleccionado")
    submit_button.click()
    human_delay(config, "Enviando login AMA")
    page.wait_for_load_state("domcontentloaded")


def _abrir_informes_periciales(page: Page, config: AppConfig) -> None:
    """Accede a la seccion de Informes Periciales.

    Notas:
        Documentacion pensada para MkDocs.

    Args:
        page: Pagina activa del portal AMA.
        config: Configuracion de la aplicacion.

    Returns:
        None.
    """

    acceso = page.locator(
        "a.btn.btn-primary[href='/gestionsiniestros/expertReportRrdd/list']"
    ).first
    acceso.wait_for(state="visible", timeout=15_000)
    human_delay(config, "Accediendo a Informes Periciales")
    acceso.click()
    page.wait_for_load_state("domcontentloaded")


def _buscar_siniestros(
    page: Page, config: AppConfig, notas: List[Dict[str, str]]
) -> None:
    """Busca los siniestros usando el formulario de busqueda.

    Notas:
        Documentacion pensada para MkDocs.

    Args:
        page: Pagina activa del portal AMA.
        config: Configuracion de la aplicacion.
        notas: Lista de notas con codigo y texto.

    Returns:
        None.
    """

    input_siniestro = page.locator("#accidentNumber").first
    boton_buscar = page.locator("button[name='_action_list']").first
    tabla_resultados = page.locator("#tableExportReportRrddList").first

    input_siniestro.wait_for(state="visible", timeout=15_000)
    boton_buscar.wait_for(state="visible", timeout=15_000)

    for nota in notas:
        codigo = str(nota.get("codigo", "")).strip()
        if not codigo:
            continue
        human_delay(config, f"Ingresando siniestro {codigo}")
        input_siniestro.click()
        input_siniestro.fill("")
        input_siniestro.type(codigo, delay=75)
        human_delay(config, "Ejecutando busqueda AMA")
        boton_buscar.click()
        page.wait_for_load_state("domcontentloaded")
        tabla_resultados.wait_for(state="visible", timeout=15_000)
        _abrir_ultimo_resultado(tabla_resultados, config)
        _abrir_agenda_asegurado(page, config)
        _abrir_agenda_modal(page, config, nota)
        _completar_agenda_modal(page, config, nota)


def _abrir_ultimo_resultado(tabla: Locator, config: AppConfig) -> None:
    """Abre el ultimo siniestro listado en la tabla de resultados.

    Notas:
        Documentacion pensada para MkDocs.

    Args:
        tabla: Tabla de resultados ya visible.
        config: Configuracion de la aplicacion.

    Returns:
        None.
    """

    filas = tabla.locator("tbody tr")
    filas.last.wait_for(state="visible", timeout=15_000)
    ultimo = filas.last
    enlace = ultimo.locator(
        "td:first-child a[href^='/gestionsiniestros/expertReportRrdd/edit/']"
    ).first
    enlace.wait_for(state="visible", timeout=15_000)
    human_delay(config, "Abriendo ultimo siniestro en AMA")
    enlace.click()


def _abrir_agenda_asegurado(page: Page, config: AppConfig) -> None:
    """Abre la pestana Agenda Asegurado.

    Notas:
        Documentacion pensada para MkDocs.

    Args:
        page: Pagina activa del portal AMA.
        config: Configuracion de la aplicacion.

    Returns:
        None.
    """

    agenda = page.locator("#agendaLiA").first
    agenda.wait_for(state="visible", timeout=15_000)
    human_delay(config, "Abriendo Agenda Asegurado")
    agenda.click()
    page.wait_for_load_state("domcontentloaded")


def _esperar_modal_agenda(
    page: Page, config: AppConfig, modal_objetivo: str, modal_otro: str
) -> None:
    """Espera el modal objetivo y cierra el otro si aparece.

    Notas:
        Documentacion pensada para MkDocs.

    Args:
        page: Pagina activa del portal AMA.
        config: Configuracion de la aplicacion.
        modal_objetivo: Selector del modal esperado.
        modal_otro: Selector del modal a cerrar si aparece.

    Returns:
        None.
    """

    objetivo = page.locator(modal_objetivo).first
    objetivo.wait_for(state="visible", timeout=15_000)
    _cerrar_modal_si_visible(page, modal_otro, None, config)


def _cerrar_modales_agenda(page: Page, config: AppConfig) -> None:
    """Cierra los modales de agenda si quedaron abiertos.

    Notas:
        Documentacion pensada para MkDocs.

    Args:
        page: Pagina activa del portal AMA.
        config: Configuracion de la aplicacion.

    Returns:
        None.
    """

    _cerrar_modal_si_visible(page, "#nuevoContactoModal", "#closeNuevoContactoForm", config)
    _cerrar_modal_si_visible(page, "#nuevaCitaModal", "#closeNuevaCitaForm", config)


def _cerrar_modal_si_visible(
    page: Page,
    modal_selector: str,
    close_selector: str | None,
    config: AppConfig,
) -> None:
    """Cierra un modal si esta visible usando su boton de cierre.

    Notas:
        Documentacion pensada para MkDocs.

    Args:
        page: Pagina activa del portal AMA.
        modal_selector: Selector del modal.
        close_selector: Selector del boton de cierre (opcional).
        config: Configuracion de la aplicacion.

    Returns:
        None.
    """

    modal = page.locator(modal_selector).first
    try:
        if not modal.is_visible():
            return
    except Exception:
        return

    if close_selector:
        close_button = page.locator(close_selector).first
        try:
            if close_button.is_visible():
                human_delay(config, "Cerrando modal no deseado")
                close_button.click()
                return
        except Exception:
            return


def _abrir_agenda_modal(
    page: Page, config: AppConfig, nota: Dict[str, str]
) -> None:
    """Abre el modal de agenda segun exista fecha.

    Notas:
        Documentacion pensada para MkDocs.

    Args:
        page: Pagina activa del portal AMA.
        config: Configuracion de la aplicacion.
        nota: Nota con codigo, fecha_visita y texto.

    Returns:
        None.
    """

    fecha_visita = str(nota.get("fecha_visita", "")).strip()
    _cerrar_modales_agenda(page, config)
    if fecha_visita:
        boton = page.locator("#buttonCita").first
        descripcion = "Nueva Cita"
        modal_objetivo = "#nuevaCitaModal"
        modal_otro = "#nuevoContactoModal"
    else:
        boton = page.locator(
            "button[data-target='#nuevoContactoModal']"
        ).first
        descripcion = "Nuevo Contacto"
        modal_objetivo = "#nuevoContactoModal"
        modal_otro = "#nuevaCitaModal"

    boton.wait_for(state="visible", timeout=15_000)
    human_delay(config, f"Abriendo {descripcion} en AMA")
    boton.click()
    _esperar_modal_agenda(page, config, modal_objetivo, modal_otro)


def _completar_agenda_modal(
    page: Page, config: AppConfig, nota: Dict[str, str]
) -> None:
    """Completa el modal de agenda segun exista fecha.

    Notas:
        Documentacion pensada para MkDocs.

    Args:
        page: Pagina activa del portal AMA.
        config: Configuracion de la aplicacion.
        nota: Nota con codigo, fecha_visita y texto.

    Returns:
        None.
    """

    fecha_visita = str(nota.get("fecha_visita", "")).strip()
    texto = str(nota.get("texto", "")).strip()

    if fecha_visita:
        _esperar_modal_agenda(page, config, "#nuevaCitaModal", "#nuevoContactoModal")
        _completar_modal_nueva_cita(page, config, fecha_visita, texto)
    else:
        _esperar_modal_agenda(page, config, "#nuevoContactoModal", "#nuevaCitaModal")
        _completar_modal_nuevo_contacto(page, config, texto)


def _completar_modal_nuevo_contacto(
    page: Page, config: AppConfig, texto: str
) -> None:
    """Completa el modal de Nuevo Contacto.

    Notas:
        Documentacion pensada para MkDocs.

    Args:
        page: Pagina activa del portal AMA.
        config: Configuracion de la aplicacion.
        texto: Texto de la nota.

    Returns:
        None.
    """

    modal = page.locator("#nuevoContactoModal").first
    modal.wait_for(state="visible", timeout=15_000)
    _cerrar_modal_si_visible(page, "#nuevaCitaModal", "#closeNuevaCitaForm", config)
    textarea = modal.locator("textarea#observaciones").first
    boton_aceptar = modal.locator("button.btn.btn-success[type='submit']").first

    textarea.wait_for(state="visible", timeout=15_000)
    boton_aceptar.wait_for(state="visible", timeout=15_000)
    human_delay(config, "Completando anotaciones de contacto")
    textarea.click()
    textarea.fill("")
    textarea.type(texto, delay=75)
    human_delay(config, "Confirmando nuevo contacto")
    boton_aceptar.click()
    page.wait_for_load_state("domcontentloaded")
    _volver_a_lista_informes(page, config)


def _completar_modal_nueva_cita(
    page: Page, config: AppConfig, fecha_visita: str, texto: str
) -> None:
    """Completa el modal de Nueva Cita.

    Notas:
        Documentacion pensada para MkDocs.

    Args:
        page: Pagina activa del portal AMA.
        config: Configuracion de la aplicacion.
        fecha_visita: Fecha de visita.
        texto: Texto de la nota.

    Returns:
        None.
    """

    modal = page.locator("#nuevaCitaModal").first
    modal.wait_for(state="visible", timeout=15_000)
    _cerrar_modal_si_visible(page, "#nuevoContactoModal", "#closeNuevoContactoForm", config)
    fecha_input = modal.locator("#fechaNuevaCitaAgenda").first
    textarea = modal.locator("textarea#observaciones").first
    boton_aceptar = modal.locator("button.btn.btn-success[type='submit']").first

    fecha_input.wait_for(state="visible", timeout=15_000)
    textarea.wait_for(state="visible", timeout=15_000)
    boton_aceptar.wait_for(state="visible", timeout=15_000)

    fecha_con_hora = _formatear_fecha_con_hora(fecha_visita)
    human_delay(config, "Completando fecha de cita")
    fecha_input.click()
    fecha_input.fill("")
    fecha_input.type(fecha_con_hora, delay=75)
    human_delay(config, "Completando anotaciones de cita")
    textarea.click()
    textarea.fill("")
    textarea.type(texto, delay=75)
    human_delay(config, "Confirmando nueva cita")
    boton_aceptar.click()
    page.wait_for_load_state("domcontentloaded")
    _volver_a_lista_informes(page, config)


def _volver_a_lista_informes(page: Page, config: AppConfig) -> None:
    """Vuelve a la lista de informes periciales.

    Notas:
        Documentacion pensada para MkDocs.

    Args:
        page: Pagina activa del portal AMA.
        config: Configuracion de la aplicacion.

    Returns:
        None.
    """

    enlace = page.locator(
        "a[href='/gestionsiniestros/expertReportRrdd/list']"
    ).first
    enlace.wait_for(state="visible", timeout=15_000)
    human_delay(config, "Volviendo a Informes Periciales")
    enlace.click()
    page.wait_for_load_state("domcontentloaded")


def _formatear_fecha_con_hora(fecha_visita: str) -> str:
    """Anade la hora por defecto si la fecha no la incluye.

    Notas:
        Documentacion pensada para MkDocs.

    Args:
        fecha_visita: Fecha en formato dd/mm/yyyy o dd/mm/yyyy HH:MM.

    Returns:
        Fecha con hora en formato dd/mm/yyyy HH:MM.
    """

    valor = fecha_visita.strip()
    if not valor:
        return ""
    if " " in valor:
        return valor
    return f"{valor} 00:00"
