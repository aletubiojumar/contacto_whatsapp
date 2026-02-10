"""Pantalla donde se captura el código de siniestro o encargo."""

from __future__ import annotations
from playwright.sync_api import FrameLocator, Page, expect
from utils.logging_utils import get_logger

class NumeroSiniestroPage:
    """Encapsula las interacciones con el formulario de búsqueda de siniestros."""

    iframe_selector = "iframe[name='appArea']"
    siniestro_input = "#claimNumber"
    enviar_button = "div.sectionButton:has-text('Enviar')"
    result_table = "#ordersList_tbody"
    # Alias por compatibilidad con referencias externas existentes.
    IFRAME_SELECTOR = iframe_selector
    SINIESTRO_INPUT = siniestro_input
    ENVIAR_BUTTON = enviar_button
    RESULT_TABLE = result_table

    # Documentación MkDocs:
    # - Propósito: preparar el formulario dentro del iframe correspondiente.
    # - Entradas: scope con página o frame.
    # - Salidas: ninguna.
    def __init__(self, scope: Page | FrameLocator) -> None:
        """Inicializa el objeto de página.

        Args:
            scope: Página o frame donde vive el formulario.

        Returns:
            None.
        """
        self.scope = scope
        if isinstance(scope, Page):
            self.frame = scope.frame_locator(self.iframe_selector)
        else:
            self.frame = scope

    # Documentación MkDocs:
    # - Propósito: esperar el estado listo del formulario.
    # - Entradas: ninguna.
    # - Salidas: ninguna.
    def wait_until_ready(self) -> None:
        """Espera a que el input de siniestro esté presente, visible y habilitado.

        Returns:
            None.
        """
        if hasattr(self.scope, "wait_for_load_state"):
            try:
                self.scope.wait_for_load_state("domcontentloaded")
            except Exception:
                pass

        locator = self.frame.locator(self.siniestro_input)
        locator.wait_for(state="visible", timeout=60_000)
        expect(locator).to_be_visible()
        expect(locator).to_be_enabled()

    # Documentación MkDocs:
    # - Propósito: cargar el código de siniestro en el formulario.
    # - Entradas: codigo de siniestro.
    # - Salidas: ninguna.
    def fill_siniestro_number(self, codigo: str) -> None:
        """Introduce el código numérico proporcionado en el campo correspondiente.

        Args:
            codigo: Código del siniestro a ingresar.

        Returns:
            None.
        """
        logger = get_logger(siniestro=codigo, tarea="ingresar_siniestro")
        logger.info("Ingresando siniestro")

        input_box = self.frame.locator(self.siniestro_input)
        input_box.click()
        # Limpiar primero y usar fill en lugar de type.
        input_box.fill("")
        input_box.fill(codigo)
        expect(input_box).to_have_value(codigo, timeout=10_000)

    # Documentación MkDocs:
    # - Propósito: enviar el formulario para iniciar la búsqueda.
    # - Entradas: ninguna.
    # - Salidas: ninguna.
    def submit_codigo(self) -> None:
        """Hace clic en el botón Enviar para confirmar el código.

        Returns:
            None.
        """
        boton = self.frame.locator(self.enviar_button)
        expect(boton).to_be_visible()
        boton.click()

    # Documentación MkDocs:
    # - Propósito: seleccionar el resultado que coincide con el código.
    # - Entradas: codigo del siniestro.
    # - Salidas: ninguna.
    def seleccionar_resultado_por_codigo(self, codigo: str) -> None:
        """Selecciona la fila correspondiente al código en la tabla de resultados.

        Args:
            codigo: Código de siniestro a seleccionar.

        Returns:
            None.
        """
        logger = get_logger(siniestro=codigo, tarea="seleccionar_resultado")
        logger.info("Esperando resultados del siniestro")

        tbody = self.frame.locator(self.result_table)
        expect(tbody).to_be_visible()
        row_locator = tbody.locator("tr.table-row")
        row_locator.first.wait_for(state="visible", timeout=15_000)
        target_row = row_locator.filter(has_text=codigo)
        if target_row.count() == 0:
            raise RuntimeError(
                f"No se encontró una fila para el código {codigo}."
            )
        objetivo = target_row.first
        objetivo.click()
