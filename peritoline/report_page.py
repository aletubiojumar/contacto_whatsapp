"""Page object para generar/descargar el Excel en Peritoline."""

from __future__ import annotations

from playwright.sync_api import Page, TimeoutError, expect

from config import AppConfig
from utils.human import human_delay


class PeritolineReportPage:
    """Acciones sobre la pagina de reportes."""

    VIEW_ALL_BUTTON = "a.btn.peritoadmins:has-text('VER ENCARGOS DE TODOS')"
    VIEW_ALL_LIST_BUTTON = "a#s-todos-button.btn.btn-primary.btn-sm"
    INSURER_SELECT = "#aseguradora"
    DOWNLOAD_BUTTON = "a#s-imprimir-button[data-original-title='Excel']"

    def __init__(self, page: Page) -> None:
        """Inicializa el page object.

        Args:
            page: Pagina de Playwright.

        Returns:
            None.
        """

        self.page = page

    def wait_until_ready(self) -> None:
        """Espera a que la pantalla de reportes este lista.

        Se acepta la presencia del boton "VER ENCARGOS DE TODOS" o del select
        de aseguradoras, segun el estado de la pagina.

        Returns:
            None.
        """

        try:
            expect(self.page.locator(self.VIEW_ALL_BUTTON)).to_be_visible()
        except AssertionError:
            expect(self.page.locator(self.INSURER_SELECT)).to_be_visible()

    def select_insurer(self, label: str) -> None:
        """Selecciona una aseguradora en el desplegable.

        Args:
            label: Nombre de la aseguradora tal como aparece en el select.

        Returns:
            None.
        """

        selector = self.page.locator(self.INSURER_SELECT)
        expect(selector).to_be_visible()
        selector.select_option(label=label)

    def download_excel(self, config: AppConfig) -> None:
        """Dispara la descarga del Excel.

        Args:
            config: Configuracion de la aplicacion.

        Returns:
            None.
        """

        self.download_excel_for_insurer(config, "ALLIANZ")

    def download_excel_for_insurer(
        self,
        config: AppConfig,
        insurer_label: str,
        click_view_all_button: bool = True,
        click_view_all_list: bool = True,
    ) -> None:
        """Dispara la descarga del Excel para una aseguradora.

        Args:
            config: Configuracion de la aplicacion.
            insurer_label: Nombre de la aseguradora en el select.
            click_view_all_button: Si se debe pulsar "VER ENCARGOS DE TODOS".
            click_view_all_list: Si se debe pulsar "VER TODOS".

        Returns:
            None.
        """

        if click_view_all_button:
            boton_all = self.page.locator(self.VIEW_ALL_BUTTON).first
            try:
                boton_all.scroll_into_view_if_needed(timeout=5_000)
                boton_all.click()
                expect(self.page.locator(self.VIEW_ALL_LIST_BUTTON)).to_be_visible()
            except TimeoutError:
                pass
            except Exception:
                pass
        human_delay(config, f"Seleccionando aseguradora {insurer_label}")
        self.select_insurer(insurer_label)
        if click_view_all_list:
            boton_ver_todos = self.page.locator(self.VIEW_ALL_LIST_BUTTON).first
            try:
                boton_ver_todos.scroll_into_view_if_needed(timeout=5_000)
                human_delay(config, "Aplicando filtro 'Ver todos'")
                boton_ver_todos.click()
            except TimeoutError:
                pass
            except Exception:
                pass
        boton_descarga = self.page.locator(self.DOWNLOAD_BUTTON).first
        expect(boton_descarga).to_be_visible()
        boton_descarga.click()
