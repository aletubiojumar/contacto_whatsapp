"""Acciones dentro de la pestana de Ficha Gestion (navegacion superior)."""

from __future__ import annotations

from playwright.sync_api import Page, expect


class NotaTabPage:
    """Permite interactuar con el menu superior para abrir la seccion 'Nota'."""

    NOTA_LINK = "ul.c-main-navbar__list a:has(span:has-text('Nota'))"
    BUSCAR_MODELO_ICON = "#lupa_span"
    CONTENIDO_TEXTAREA = "textarea#texto"
    GRABAR_BUTTON = "#butGrabar"

    def __init__(self, page: Page) -> None:
        """Inicializa el page object.

        Args:
            page: Pagina de Playwright.

        Returns:
            None.
        """

        self.page = page

    def abrir_seccion_nota(self) -> None:
        """Hace clic en el enlace 'Nota' de la barra superior.

        Returns:
            None.
        """

        enlace = self.page.locator(self.NOTA_LINK).first
        enlace.scroll_into_view_if_needed()
        expect(enlace).to_be_visible()
        enlace.click()

    def abrir_busqueda_modelo(self) -> None:
        """Dispara la lupa 'Buscar modelo' dentro de la nota.

        Returns:
            None.
        """

        boton = self.page.locator(self.BUSCAR_MODELO_ICON)
        boton.scroll_into_view_if_needed()
        expect(boton).to_be_visible()
        boton.click()

    def rellenar_texto(self, contenido: str) -> None:
        """Rellena el area de texto principal de la nota.

        Args:
            contenido: Texto a escribir.

        Returns:
            None.
        """

        text_area = self.page.locator(self.CONTENIDO_TEXTAREA)
        text_area.scroll_into_view_if_needed()
        text_area.click()
        text_area.fill(contenido)

    def grabar_nota(self) -> None:
        """Pulsa el boton 'Grabar' para guardar la nota.

        Returns:
            None.
        """

        boton = self.page.locator(self.GRABAR_BUTTON)
        boton.scroll_into_view_if_needed()
        expect(boton).to_be_enabled()
        boton.click()
