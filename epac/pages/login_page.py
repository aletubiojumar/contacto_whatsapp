"""Objeto de página asociado a la pantalla de inicio de sesión del portal."""

from __future__ import annotations

import os

from playwright.sync_api import Page, expect


class LoginPage:
    """Representa el formulario donde se envían las credenciales del usuario."""

    username_input_selector = 'input[name="username"]'
    password_input_selector = 'input[name="password"]'
    submit_button_selector = 'button[type="submit"]'

    # Documentación MkDocs:
    # - Propósito: preparar el objeto de login con la página activa.
    # - Entradas: page con la sesión activa.
    # - Salidas: ninguna.
    def __init__(self, page: Page) -> None:
        """Inicializa el objeto de página.

        Args:
            page: Página de Playwright.

        Returns:
            None.
        """

        self.page = page

    # Documentación MkDocs:
    # - Propósito: navegar a la URL de login y validar el formulario.
    # - Entradas: url de inicio de sesión.
    # - Salidas: ninguna.
    def open(self, url: str) -> None:
        """Navega a la URL de login y espera hasta que aparezca el formulario.

        Args:
            url: URL de inicio de sesión.

        Returns:
            None.
        """

        self.page.goto(url)
        expect(
            self.page.locator(self.username_input_selector)
        ).to_be_visible()

    # Documentación MkDocs:
    # - Propósito: completar credenciales con parámetros o variables de entorno.
    # - Entradas: username y password opcionales.
    # - Salidas: ninguna.
    def login(self, username: str | None = None, password: str | None = None) -> None:
        """Completa las credenciales (o las toma del entorno) y las envía.

        Args:
            username: Usuario opcional.
            password: Password opcional.

        Returns:
            None.
        """

        username = username or self._env_or_raise("APP_USERNAME")
        password = password or self._env_or_raise("APP_PASSWORD")
        self.page.fill(self.username_input_selector, username)
        self.page.fill(self.password_input_selector, password)
        self.page.click(self.submit_button_selector)

    # Documentación MkDocs:
    # - Propósito: obtener una variable de entorno obligatoria.
    # - Entradas: key con el nombre de la variable.
    # - Salidas: valor de la variable.
    def _env_or_raise(self, key: str) -> str:
        """Obtiene una variable de entorno o lanza una excepción explicativa.

        Args:
            key: Nombre de la variable de entorno.

        Returns:
            Valor de la variable de entorno.
        """

        value = os.getenv(key)
        if not value:
            raise RuntimeError(
                f"Variable de entorno '{key}' no está definida. "
                "Configúrala en tu archivo .env o en el entorno de ejecución."
            )
        return value
