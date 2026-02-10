"""Flujo de descarga del Excel de Peritoline."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page

from config import AppConfig
from utils.human import human_delay
from peritoline.login_page import PeritolineLoginPage
from peritoline.report_page import PeritolineReportPage


def _cerrar_popup_avisos_si_existe(page: Page, config: AppConfig) -> None:
    """Cierra el popup de avisos si aparece tras el login.

    Args:
        page: Pagina activa.
        config: Configuracion de la aplicacion.

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


def download_report(
    page: Page,
    config: AppConfig,
    login_url: str,
    output_path: Path,
    username: str,
    password: str,
) -> Path:
    """Inicia sesion, navega a reportes y descarga el Excel.

    El output_path debe apuntar a la ruta final del archivo.

    Args:
        page: Pagina activa.
        config: Configuracion de la aplicacion.
        login_url: URL de login de Peritoline.
        output_path: Ruta final del archivo Excel.
        username: Usuario de Peritoline.
        password: Password de Peritoline.

    Returns:
        Ruta del archivo descargado.
    """

    login_page = PeritolineLoginPage(page)
    login_page.open(login_url)
    human_delay(config, "Login Peritoline")
    login_page.login(username, password)
    human_delay(config, "Esperando post-login")
    _cerrar_popup_avisos_si_existe(page, config)

    report_page = PeritolineReportPage(page)
    report_page.wait_until_ready()
    human_delay(config, "Abriendo encargos de todos")

    with page.expect_download(timeout=config.upload_timeout_ms) as download_info:
        report_page.download_excel(config)
    download = download_info.value
    output_path.parent.mkdir(parents=True, exist_ok=True)
    download.save_as(str(output_path))
    return output_path


def download_report_in_session(
    page: Page,
    config: AppConfig,
    output_path: Path,
    insurer_label: str,
    click_view_all_button: bool = True,
    click_view_all_list: bool = True,
) -> Path:
    """Descarga un Excel para una aseguradora usando la sesion actual.

    Args:
        page: Pagina activa.
        config: Configuracion de la aplicacion.
        output_path: Ruta final del archivo Excel.
        insurer_label: Aseguradora seleccionada en el desplegable.
        click_view_all_button: Si se debe pulsar "VER ENCARGOS DE TODOS".
        click_view_all_list: Si se debe pulsar "VER TODOS".

    Returns:
        Ruta del archivo descargado.
    """

    report_page = PeritolineReportPage(page)
    report_page.wait_until_ready()
    human_delay(config, f"Abriendo encargos de {insurer_label}")

    with page.expect_download(timeout=config.upload_timeout_ms) as download_info:
        report_page.download_excel_for_insurer(
            config,
            insurer_label,
            click_view_all_button=click_view_all_button,
            click_view_all_list=click_view_all_list,
        )
    download = download_info.value
    output_path.parent.mkdir(parents=True, exist_ok=True)
    download.save_as(str(output_path))
    return output_path
