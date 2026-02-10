from playwright.sync_api import Page, expect
from utils.logging_utils import get_logger


class MenuLateralPage:
    IFRAME_SELECTOR = "iframe[name='appArea']"

    HSC_FP_NODE = "div.divOptionTreeMenu:has-text('HSC y FP')"
    FICHA_PERITACION_NODE = "div.divOptionTreeMenu:has-text('Ficha peritación')"

    def __init__(self, page: Page, siniestro: str = "sin_codigo"):
        self.page = page                 # ✅ GUARDAR PAGE
        self.frame = page.frame_locator(self.IFRAME_SELECTOR)
        self.siniestro = siniestro

    def abrir_ficha_peritacion(self) -> None:
        logger = get_logger(
            siniestro=self.siniestro,
            tarea="abrir_ficha_peritacion"
        )

        logger.info("Abriendo menú HSC y FP")

        hsc = self.frame.locator(self.HSC_FP_NODE).first
        expect(hsc).to_be_visible(timeout=15_000)
        hsc.click()

        logger.info("Seleccionando Ficha peritación")

        ficha = self.frame.locator(self.FICHA_PERITACION_NODE).first
        expect(ficha).to_be_visible(timeout=15_000)
        ficha.click()

        self.page.wait_for_timeout(500)
