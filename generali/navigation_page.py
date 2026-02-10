"""Page object para la navegacion inicial en Generali."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING
import time

from playwright.sync_api import Frame, FrameLocator, Page, TimeoutError, expect

from utils.human import human_delay

if TYPE_CHECKING:
    from config import Config


class GeneraliNavigationPage:
    """Encapsula los pasos iniciales para llegar al filtro de siniestros."""

    GENERALI_LINK = "a#generali_link"
    PLATAFORMA_WEB_LINK = "a:has-text('Plataforma Web')"
    POPUP_CAMBIO_PROCESO = "div#avisoCambioProceso"
    POPUP_CONTINUAR_BUTTON = "input#avisoCambioProceso\\.continuar"
    VER_TODOS_BUTTONS = (
        "div#orderDesktop input.buttonSeeAll.linkOrders[value='VER TODOS']",
        "div.module#orderDesktop input.buttonSeeAll.linkOrders[value='VER TODOS']",
        "input.right.button.buttonSeeAll.linkOrders[value='VER TODOS']",
    )
    GENERALI_FRAMES = (
        "iframe#mainFrame",
        "iframe[name='mainFrame']",
        "iframe[src*='processDesktop']",
        "iframe[name='areaTrabajo']",
        "iframe#areaTrabajo",
        "iframe[src*='sin_profFormWeb']",
    )
    SINIESTRO_INPUT = "input[name='claimNumber']"
    FILTRAR_BUTTON = "input.buttonFilter.button[value='FILTRAR']"
    SINIESTRO_ROW = "ul.infoRow li.linkOrderDetail:has(span:has-text('{codigo}'))"
    INFORMAR_SITUACION_LINK = "a.newManagement[management='situationReport']"
    CODIGO_SITUACION_SELECT = "select.codeSituation"
    OBSERVACIONES_TEXTAREA = "textarea[name='tabOrderManagement.situationReport.observations']"
    FECHA_GESTION_INPUT = "input[name='tabOrderManagement.situationReport.date']"
    GUARDAR_BUTTON = "a.saveSituation:has-text('GUARDAR')"

    def __init__(self, page: Page, config: Optional["Config"] = None) -> None:
        """Inicializa el page object.

        Args:
            page: Pagina de Playwright.
            config: Configuracion para pausas humanas.

        Returns:
            None.
        """

        self.page = page
        self.config = config

    def abrir_generali_desde_peritoline(self) -> Page:
        """Abre Generali desde Peritoline en una nueva pestana.

        Returns:
            Pagina nueva de Generali.
        """

        with self.page.context.expect_page(timeout=20_000) as new_page_event:
            self.page.click(self.GENERALI_LINK)
        new_page = new_page_event.value
        new_page.bring_to_front()
        new_page.wait_for_load_state("domcontentloaded")
        return new_page

    def abrir_plataforma_web(self) -> None:
        """Entra en la opcion 'Plataforma Web'.

        Returns:
            None.
        """

        enlace = self.page.locator(self.PLATAFORMA_WEB_LINK).first
        expect(enlace).to_be_visible()
        enlace.click()
        self._wait_for_main_frame()

    def volver_a_plataforma_web(self, codigo: str) -> None:
        """Reabre Plataforma Web y confirma el popup si aparece.

        Args:
            codigo: Codigo del siniestro asociado.

        Returns:
            None.
        """

        enlace = self.page.locator(self.PLATAFORMA_WEB_LINK).first
        expect(enlace).to_be_visible()
        if self.config:
            human_delay(self.config, "Volviendo a Plataforma Web", siniestro=codigo)
        enlace.click()

        popup = self.page.locator(self.POPUP_CAMBIO_PROCESO)
        try:
            popup.wait_for(state="visible", timeout=5_000)
        except TimeoutError:
            self._wait_for_main_frame()
            return

        boton = popup.locator(self.POPUP_CONTINUAR_BUTTON).first
        if self.config:
            human_delay(self.config, "Confirmando cambio de proceso", siniestro=codigo)
        boton.click()
        self._wait_for_main_frame()

    def click_ver_todos(self, timeout_ms: int = 20_000) -> None:
        """Pulsa el boton 'VER TODOS'.

        Args:
            timeout_ms: Tiempo maximo de espera en ms.

        Returns:
            None.
        """

        main_scope = self._get_main_frame_locator()
        for selector in self.VER_TODOS_BUTTONS:
            locator = main_scope.locator(selector)
            try:
                locator.wait_for(state="visible", timeout=timeout_ms)
                boton = locator.last
                boton.scroll_into_view_if_needed()
                boton.click()
                return
            except TimeoutError:
                continue

        raise RuntimeError("No se encontro un boton 'VER TODOS' en Generali.")

    def filtrar_por_siniestro(self, codigo: str) -> None:
        """Introduce el siniestro y pulsa Filtrar.

        Args:
            codigo: Codigo del siniestro a buscar.

        Returns:
            None.
        """

        scope = self._get_main_frame_locator()
        campo = scope.locator(self.SINIESTRO_INPUT).first
        try:
            expect(campo).to_be_visible()
        except Exception:
            scope = self._resolve_scope_for_selector(self.SINIESTRO_INPUT)
            campo = scope.locator(self.SINIESTRO_INPUT).first
            expect(campo).to_be_visible()
        if self.config:
            human_delay(self.config, "Preparando campo siniestro", siniestro=codigo)
        campo.fill("")
        delay_ms = 50
        if self.config:
            delay_ms = max(30, min(120, int(self.config.slow_mo_ms / 5)))
        campo.type(codigo, delay=delay_ms)

        boton = scope.locator(self.FILTRAR_BUTTON).first
        expect(boton).to_be_visible()
        if self.config:
            human_delay(self.config, "Aplicando filtro siniestro", siniestro=codigo)
        boton.click()

    def abrir_siniestro(self, codigo: str, timeout_ms: int = 20_000) -> None:
        """Abre la ficha del siniestro haciendo click en la fila.

        Args:
            codigo: Codigo del siniestro a abrir.
            timeout_ms: Tiempo maximo de espera en ms.

        Returns:
            None.
        """

        scope = self._get_main_frame_locator()
        selector = self.SINIESTRO_ROW.format(codigo=codigo)
        fila = scope.locator(selector).first
        fila.wait_for(state="visible", timeout=timeout_ms)
        if self.config:
            human_delay(self.config, "Abriendo siniestro", siniestro=codigo)
        fila.click()

    def informar_situacion(self, codigo: str, timeout_ms: int = 20_000) -> None:
        """Abre la seccion de informar situacion.

        Args:
            codigo: Codigo del siniestro asociado.
            timeout_ms: Tiempo maximo de espera en ms.

        Returns:
            None.
        """

        scope = self._get_main_frame_locator()
        enlace = scope.locator(self.INFORMAR_SITUACION_LINK).first
        enlace.wait_for(state="visible", timeout=timeout_ms)
        if self.config:
            human_delay(self.config, "Informar situacion", siniestro=codigo)
        enlace.click()

    def seleccionar_codigo_situacion(
        self, codigo: str, fecha_visita: str, timeout_ms: int = 20_000
    ) -> None:
        """Selecciona el codigo de situacion segun la fecha de visita.

        Args:
            codigo: Codigo del siniestro asociado.
            fecha_visita: Fecha de visita si existe.
            timeout_ms: Tiempo maximo de espera en ms.

        Returns:
            None.
        """

        opcion = "232" if fecha_visita else "215"
        scope = self._get_main_frame_locator()
        selector = scope.locator(self.CODIGO_SITUACION_SELECT).first
        selector.wait_for(state="visible", timeout=timeout_ms)
        if self.config:
            human_delay(self.config, "Seleccionando codigo situacion", siniestro=codigo)
        selector.select_option(opcion)

    def completar_observaciones(
        self, codigo: str, texto: str, timeout_ms: int = 20_000
    ) -> None:
        """Rellena el campo de observaciones.

        Args:
            codigo: Codigo del siniestro asociado.
            texto: Texto a escribir en observaciones.
            timeout_ms: Tiempo maximo de espera en ms.

        Returns:
            None.
        """

        scope = self._get_main_frame_locator()
        campo = scope.locator(self.OBSERVACIONES_TEXTAREA).first
        campo.wait_for(state="visible", timeout=timeout_ms)
        if self.config:
            human_delay(self.config, "Completando observaciones", siniestro=codigo)
        campo.fill("")
        campo.type(texto, delay=50)

    def completar_fecha_gestion(
        self, codigo: str, fecha_visita: str, timeout_ms: int = 20_000
    ) -> None:
        """Rellena la fecha de gestion con la visita.

        Args:
            codigo: Codigo del siniestro asociado.
            fecha_visita: Fecha de visita a colocar.
            timeout_ms: Tiempo maximo de espera en ms.

        Returns:
            None.
        """

        scope = self._get_main_frame_locator()
        campo = scope.locator(self.FECHA_GESTION_INPUT).first
        campo.wait_for(state="visible", timeout=timeout_ms)
        if self.config:
            human_delay(self.config, "Completando fecha gestion", siniestro=codigo)
        campo.fill("")
        campo.type(fecha_visita, delay=50)

    def guardar_situacion(self, codigo: str, timeout_ms: int = 20_000) -> None:
        """Pulsa el boton GUARDAR de la situacion.

        Args:
            codigo: Codigo del siniestro asociado.
            timeout_ms: Tiempo maximo de espera en ms.

        Returns:
            None.
        """

        scope = self._get_main_frame_locator()
        boton = scope.locator(self.GUARDAR_BUTTON).first
        boton.wait_for(state="visible", timeout=timeout_ms)
        if self.config:
            human_delay(self.config, "Guardando situacion", siniestro=codigo)
        boton.click()


    def _find_scope_for_selector(self, selector: str) -> Page | Frame | None:
        """Busca el selector en la pagina o en iframes sin bloquear.

        Args:
            selector: Selector CSS a localizar.

        Returns:
            Page o FrameLocator donde existe el selector, o None.
        """

        if self.page.locator(selector).count() > 0:
            return self.page

        for frame in self.page.frames:
            try:
                if frame.locator(selector).count() > 0:
                    return frame
            except Exception:
                continue

        return None

    def _get_main_frame_locator(self) -> FrameLocator | Page:
        """Devuelve un locator del iframe principal anidado.

        Returns:
            FrameLocator o Page principal para la navegacion.
        """

        area_locator = self._get_area_trabajo_locator()
        if area_locator:
            return area_locator.frame_locator("iframe#mainFrame")

        frame = self._find_main_frame()
        if frame:
            return self.page.frame_locator(f"iframe[name='{frame.name}']")
        return self.page

    def _get_area_trabajo_locator(self) -> FrameLocator | None:
        """Devuelve el locator del iframe areaTrabajo si existe.

        Returns:
            FrameLocator del iframe areaTrabajo o None.
        """

        try:
            locator = self.page.frame_locator("iframe#areaTrabajo")
            if locator.locator("body").count() > 0:
                return locator
        except Exception:
            return None
        return None

    def _find_main_frame(self) -> Frame | None:
        """Localiza el iframe principal de Generali si existe.

        Returns:
            Frame principal o None si no se detecta.
        """

        def _match_frame(frame: Frame, prefer_main: bool) -> Frame | None:
            """Evalua si un frame coincide con los criterios de busqueda.

            Args:
                frame: Frame a evaluar.
                prefer_main: Prioriza el iframe principal si es True.

            Returns:
                Frame si coincide o None en caso contrario.
            """

            if prefer_main:
                if frame.name == "mainFrame" or "processDesktop" in frame.url:
                    return frame
            if frame.name == "areaTrabajo" or "profesionalHome" in frame.url:
                return frame
            if "sin_profFormWeb" in frame.url:
                return frame
            return None

        def _walk_frames(frame: Frame, prefer_main: bool) -> Frame | None:
            """Recorre frames anidados hasta encontrar uno que coincida.

            Args:
                frame: Frame raiz desde el que recorrer.
                prefer_main: Prioriza el iframe principal si es True.

            Returns:
                Frame encontrado o None si no existe.
            """

            matched = _match_frame(frame, prefer_main)
            if matched:
                return matched
            for child in frame.child_frames:
                found = _walk_frames(child, prefer_main)
                if found:
                    return found
            return None

        found = _walk_frames(self.page.main_frame, prefer_main=True)
        if found:
            return found
        return _walk_frames(self.page.main_frame, prefer_main=False)

    def _resolve_scope_for_selector(self, selector: str) -> Page | Frame:
        """Devuelve el scope donde existe el selector o falla si no aparece.

        Args:
            selector: Selector CSS a localizar.

        Returns:
            Page o Frame con el selector disponible.
        """

        scope = self._find_scope_for_selector(selector)
        if scope is None:
            raise RuntimeError(f"No se encontro el selector '{selector}' en Generali.")
        return scope

    def _wait_for_main_frame(self, timeout_ms: int = 20_000) -> None:
        """Espera a que el iframe principal cargue contenido.

        Args:
            timeout_ms: Tiempo maximo de espera en ms.

        Returns:
            None.
        """

        end_time = time.time() + (timeout_ms / 1000)
        while time.time() < end_time:
            try:
                area_locator = self._get_area_trabajo_locator()
                if area_locator:
                    area_locator.locator("body").wait_for(
                        state="attached", timeout=timeout_ms
                    )
                    main_locator = area_locator.frame_locator("iframe#mainFrame")
                    main_locator.locator("body").wait_for(
                        state="attached", timeout=timeout_ms
                    )
                    return
            except Exception:
                time.sleep(0.2)
                continue
            time.sleep(0.2)
        raise TimeoutError("No se encontro el iframe principal de Generali.")
