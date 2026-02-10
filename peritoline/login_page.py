"""Page object para el login en Peritoline."""

from __future__ import annotations

from playwright.sync_api import Page, expect


class PeritolineLoginPage:
    """Encapsula el formulario de autenticacion."""

    USER_INPUT = "#input-usuario"
    PASS_INPUT = "#input-password"
    SUBMIT_BUTTON = "#login-form-button"

    def __init__(self, page: Page) -> None:
        """Inicializa el page object.

        Args:
            page: Pagina de Playwright.

        Returns:
            None.
        """

        self.page = page

    def open(self, url: str) -> None:
        """Navega a la pantalla de login.

        Args:
            url: URL de login de Peritoline.

        Returns:
            None.
        """

        self.page.goto(url)
        expect(self.page.locator(self.USER_INPUT)).to_be_visible()

    def login(self, username: str, password: str) -> None:
        """Rellena credenciales y envia el formulario.

        Args:
            username: Usuario de Peritoline.
            password: Password de Peritoline.

        Returns:
            None.
        """

        self.page.click(self.USER_INPUT)
        self.page.fill(self.USER_INPUT, username)

        password_input = self.page.locator(self.PASS_INPUT)
        password_input.click()
        # Algunos formularios dejan el input en readonly hasta hacer focus.
        password_input.evaluate("el => el.removeAttribute('readonly')")
        password_input.fill(password)
        self.page.click(self.SUBMIT_BUTTON)
