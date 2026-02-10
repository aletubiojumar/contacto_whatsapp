"""Objetos de navegacion para moverse entre menus y submenus del portal."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from config import AppConfig


class NavigationPage:
    """Agrupa las acciones de navegacion necesarias justo despues del login."""

    def __init__(self, page: Page, config: AppConfig) -> None:
        """Inicializa el page object.

        Args:
            page: Pagina de Playwright.
            config: Configuracion de la aplicacion.

        Returns:
            None.
        """

        self.page = page
        self.config = config

    def goto_informe_pericial_diversos_sea(self) -> None:
        """Abre el submenu 'Informe Pericial Diversos SEA' dentro de Aplic. Allianz.

        Returns:
            None.
        """

        aplic_allianz_link = self.page.get_by_role(
            "menuitem", name="Aplic. Allianz", exact=True
        )
        expect(aplic_allianz_link).to_be_visible()
        aplic_allianz_link.click()

        informe_link = self.page.get_by_role(
            "menuitem", name="Informe Pericial Diversos SEA", exact=True
        )
        expect(informe_link).to_be_visible()
        informe_link.click()
