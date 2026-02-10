"""Page Object para extraer teléfono del texto de la ficha - FIX: prefijos + evitar falsos positivos."""

from __future__ import annotations

import re
from playwright.sync_api import Page

import phonenumbers
from phonenumbers import NumberParseException
from phonenumbers.phonenumberutil import number_type, PhoneNumberType


class EpacFichaPeritacionPage:
    """Extrae teléfono del texto de la ficha del siniestro."""

    IFRAME_SELECTOR = "iframe[name='appArea']"

    # Candidatos tipo teléfono: +/00 opcional + dígitos con separadores
    PHONE_CANDIDATE_RE = re.compile(r"(?:\+|00)?\s*\d[\d\s().,\-]{6,}\d",re.UNICODE)

    # Delimitadores típicos tras secciones (para no tragarnos la tabla "SINIESTROS")
    CUT_PATTERNS = [
        re.compile(r"\n\s*-{10,}\s*\n", re.MULTILINE),
        re.compile(r"\n\s*SINIESTROS\s*\n", re.IGNORECASE),
        re.compile(r"\n\s*NUMERO\s+FECHA\s+RESERVA\s+", re.IGNORECASE),
    ]

    def __init__(self, page: Page) -> None:
        self.page = page
        self.frame = page.frame_locator(self.IFRAME_SELECTOR)

    # ---------------------------
    # API pública
    # ---------------------------
    def extraer_telefono(self) -> str | None:
        """Extrae teléfono siguiendo la prioridad:
        OBSERVACIONES MANUALES -> DESCRIPCION -> TELEF-1 -> TELEF-2
        """
        try:
            texto_completo = self._obtener_texto_ficha()
            print(f"DEBUG len(texto)={len(texto_completo)} TELEF={'TELEF' in texto_completo.upper()}")

            if not texto_completo:
                print("  ⚠ No se pudo obtener el texto de la ficha")
                return None

            # 1) OBSERVACIONES MANUALES
            telefono = self._buscar_en_seccion(texto_completo, "OBSERVACIONES MANUALES:")
            if telefono:
                print(f"  ✓ Teléfono encontrado en 'OBSERVACIONES MANUALES': {telefono}")
                return telefono

            # 2) DESCRIPCION
            telefono = self._buscar_en_seccion(texto_completo, "DESCRIPCION:")
            if telefono:
                print(f"  ✓ Teléfono encontrado en 'DESCRIPCION': {telefono}")
                return telefono

            # 3) TELEF-1
            telefono = self._buscar_campo_telef(texto_completo, "TELEF-1:")
            if telefono:
                print(f"  ✓ Teléfono encontrado en 'TELEF-1': {telefono}")
                return telefono

            # 4) TELEF-2
            telefono = self._buscar_campo_telef(texto_completo, "TELEF-2:")
            if telefono:
                print(f"  ✓ Teléfono encontrado en 'TELEF-2': {telefono}")
                return telefono
            
            if not telefono:
                print("  DEBUG: muestro 20 líneas alrededor de TELEF-1/TELEF-2")
                for key in ["TELEF-1", "TELEF-2", "OBSERVACIONES MANUALES", "DESCRIPCION"]:
                    idx = texto_completo.upper().find(key)
                    if idx != -1:
                        print("\n---", key, "---")
                        print(texto_completo[max(0, idx-200): idx+400])

            print("  Aviso: no se encontró ningún teléfono")
            return None

        except Exception as e:
            print(f"  - Error en extraer_telefono: {e}")
            return None

    # ---------------------------
    # Obtención de texto
    # ---------------------------
    def _obtener_texto_ficha(self) -> str:
        """
        Obtiene el texto completo de la ficha de forma robusta:
        1) buscar un nodo dentro del iframe que contenga 'SINIESTROS'/'PERITAJE'/'TELEF'
        y devolver su textContent (sirve aunque no sea visible)
        2) fallback: body.innerText
        """
        try:
            frm = self.page.frame(name="appArea")
            if not frm:
                return ""

            frm.wait_for_selector("body", state="attached", timeout=15000)

            # 1) Intentar localizar el contenedor real de la ficha
            # Buscamos un elemento que contenga palabras clave típicas.
            # Usamos textContent (no innerText) para evitar problemas de visibilidad/render.
            for attempt in range(3):
                handle = frm.evaluate_handle(
                    """() => {
                        const needles = ["SINIESTROS", "PERITAJE", "TELEF-1", "TELEF-2"];
                        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
                        let best = null;
                        while (walker.nextNode()) {
                        const el = walker.currentNode;
                        const tc = (el.textContent || "").toUpperCase();
                        // candidato: contiene al menos 2 needles y tiene bastante texto
                        let score = 0;
                        for (const n of needles) if (tc.includes(n)) score++;
                        if (score >= 2 && tc.length > 800) {
                            best = el;
                            break;
                        }
                        }
                        return best;
                    }"""
                )

                # Si encontramos elemento, devolvemos su textContent
                if handle:
                    try:
                        txt = frm.evaluate("(el) => el ? (el.textContent || '') : ''", handle) or ""
                        txt = txt.strip()
                        if len(txt) > 800:
                            return txt
                    except Exception:
                        pass

                self.page.wait_for_timeout(400)

            # 2) Fallback: intentar pre/textarea grande
            for sel in ["pre", "textarea"]:
                try:
                    loc = frm.query_selector(sel)
                    if loc:
                        txt = frm.evaluate("(el) => el.textContent || ''", loc) or ""
                        txt = (txt or "").strip()
                        if len(txt) > 800:
                            return txt
                except Exception:
                    pass

            # 3) Último fallback: body.innerText
            txt = frm.evaluate("() => document.body ? document.body.innerText : ''") or ""
            return (txt or "").strip()

        except Exception as e:
            print(f"  ERROR obteniendo texto ficha: {e}")
            return ""

    # ---------------------------
    # Búsquedas por prioridad
    # ---------------------------
    def _buscar_en_seccion(self, texto: str, etiqueta_seccion: str) -> str | None:
        """Busca teléfono dentro de una sección de texto (cortando antes de tablas/delimitadores)."""
        try:
            pos = texto.rfind(etiqueta_seccion)
            if pos == -1:
                return None

            # Tomar desde justo después del label
            start = pos + len(etiqueta_seccion)
            chunk = texto[start:]

            # Cortar por delimitadores típicos (para evitar pillar números de tablas)
            cut_idx = None
            for pat in self.CUT_PATTERNS:
                m = pat.search(chunk)
                if m:
                    if cut_idx is None or m.start() < cut_idx:
                        cut_idx = m.start()

            if cut_idx is not None:
                chunk = chunk[:cut_idx]

            # Limitamos tamaño igualmente (sección “real”)
            chunk = chunk[:400]

            return self._extraer_numero_telefono(chunk)

        except Exception as e:
            print(f"  - Error buscando en sección '{etiqueta_seccion}': {e}")
            return None

    def _buscar_campo_telef(self, texto: str, campo: str) -> str | None:
        # Busca teléfono en TELEF-1 / TELEF-2 aunque el texto venga como:
        #   - "TELEF-1:00685789868"
        #   - "TELEF-1 : 00685789868"
        #   - "TELEF-1 00685789868"
        # y aunque lleve puntos/comas/espacios.

        try:
            campo_base = campo.replace(":", "").strip()   # TELEF-1 / TELEF-2
            patron = rf"{re.escape(campo_base)}\s*:?\s*([+0-9][0-9\s().,\-]{{6,}})"
            m = re.search(patron, texto, flags=re.IGNORECASE)
            if not m:
                return None

            valor = m.group(1)
            # cortar por "HORA" si existe
            valor = re.split(r"\bHORA\b", valor, flags=re.IGNORECASE)[0].strip()

            return self._extraer_numero_telefono(valor)

        except Exception as e:
            print(f"  - Error buscando campo '{campo}': {e}")
            return None

    # ---------------------------
    # Extracción + normalización
    # ---------------------------
    def _extraer_numero_telefono(self, texto: str) -> str | None:
        if not texto:
            return None

        for m in self.PHONE_CANDIDATE_RE.finditer(texto):
            candidato = m.group(0)
            tel = self._normalizar_telefono(candidato)
            if not tel:
                continue

            if self._es_movil(tel):
                # Si es ES nacional ya viene como 9 dígitos
                # Si es extranjero vendrá como +XXXXXXXX
                return tel

        return None

    def _normalizar_telefono(self, raw: str) -> str | None:
        if not raw:
            return None

        s = raw.strip()

        # Quita separadores típicos
        s = s.replace("\u00A0", " ").strip()

        # Caso ePAC: 00 + 9 dígitos españoles (sin país). No es internacional real.
        if s.startswith("00"):
            rest_digits = re.sub(r"\D", "", s[2:])
            # móvil ES
            if len(rest_digits) == 9 and rest_digits[0] in "67":
                return rest_digits
            # fijo ES (lo devolvemos igualmente para que luego _es_movil lo descarte)
            if len(rest_digits) == 9 and rest_digits[0] in "89":
                return rest_digits
            # si no es ES de 9 dígitos, entonces sí lo tratamos como internacional real
            s = "+" + rest_digits

        # Si ya viene con +, dejamos solo + y dígitos
        if s.startswith("+"):
            s = "+" + re.sub(r"\D", "", s[1:])
            if 8 <= (len(s) - 1) <= 15:
                return s
            return None

        # Si no viene con +, dejamos solo dígitos
        digits = re.sub(r"\D", "", s)
        if not digits:
            return None

        # ES: 0 + 9 dígitos
        if digits.startswith("0") and len(digits) == 10 and digits[1] in "6789":
            digits = digits[1:]

        # ES: 34 + 9 dígitos (sin +)
        if digits.startswith("34") and len(digits) == 11 and digits[2] in "6789":
            return digits[-9:]

        # ES: 9 dígitos (devolvemos nacional)
        if len(digits) == 9:
            return digits

        # Si parece internacional sin '+', lo devolvemos con '+'
        if 8 <= len(digits) <= 15:
            return "+" + digits

        return None


    def _es_movil(self, tel_norm: str) -> bool:
        """
        Decide si es móvil:
        - ES (sin +): móvil si empieza por 6/7
        - Con + (internacional): usa phonenumbers para clasificar (UE incluido)
        Aceptamos MOBILE y FIXED_LINE_OR_MOBILE.
        """
        if not tel_norm:
            return False

        # Caso España nacional (9 dígitos)
        if not tel_norm.startswith("+"):
            return len(tel_norm) == 9 and tel_norm[0] in "67"

        # Internacional: usa phonenumbers si está disponible
        if phonenumbers is None:
            # Fallback: si no tenemos librería, no podemos asegurar => lo aceptamos
            # para no perder móviles extranjeros.
            return True

        try:
            num = phonenumbers.parse(tel_norm, None)
            if not phonenumbers.is_valid_number(num):
                return False

            t = number_type(num)
            return t in (PhoneNumberType.MOBILE, PhoneNumberType.FIXED_LINE_OR_MOBILE)

        except NumberParseException:
            return False

