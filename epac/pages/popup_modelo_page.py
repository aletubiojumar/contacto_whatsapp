"""Ventana modal encargada de seleccionar un modelo de nota."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from utils.logging_utils import get_logger


class PopupModeloPage:
    """Encapsula la tabla de modelos disponible dentro del popup."""

    TABLA_MODELOS = "#listaTipos tbody"

    def __init__(self, page: Page, siniestro: str = "sin_codigo") -> None:
        """Inicializa el page object.

        Args:
            page: Pagina del popup.
            siniestro: Codigo del siniestro para trazabilidad.

        Returns:
            None.
        """

        self.page = page
        self.siniestro = siniestro

    def wait_until_visible(self) -> None:
        """Bloquea hasta que la ventana emergente este lista para interactuar.

        Returns:
            None.
        """

        self.page.wait_for_load_state("domcontentloaded")
        expect(self.page.locator(self.TABLA_MODELOS)).to_be_visible()

    def seleccionar_modelo(self, codigo_modelo: str) -> None:
        """Selecciona la fila cuyo codigo coincide con el argumento.

        Args:
            codigo_modelo: Codigo del modelo a seleccionar.

        Returns:
            None.
        """

        logger = get_logger(siniestro=self.siniestro, tarea="seleccionar_modelo")
        logger.info("Seleccionando modelo %s", codigo_modelo)
        tbody = self.page.locator(self.TABLA_MODELOS)
        fila = tbody.locator("tr").filter(has_text=codigo_modelo)
        if fila.count() == 0:
            raise RuntimeError(f"No se encontro el modelo {codigo_modelo}.")
        objetivo = fila.first
        objetivo.scroll_into_view_if_needed()
        with self.page.expect_event("close"):
            objetivo.click()
