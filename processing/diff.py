"""Comparacion entre reportes para obtener nuevas entradas."""

from __future__ import annotations

from typing import List, Dict, Set, Tuple


def _build_key(row: Dict) -> Tuple:
    """Clave unica por siniestro.

    Args:
        row: Fila normalizada.

    Returns:
        Clave de comparacion.
    """
    return (row.get("codigo"), row.get("fecha_intervencion"))


def compute_delta(current: List[Dict], previous: List[Dict]) -> List[Dict]:
    """Devuelve filas que estan en current pero no en previous.

    Args:
        current: Reporte actual.
        previous: Reporte anterior.

    Returns:
        Filas nuevas respecto al reporte anterior.
    """

    previous_keys: Set[Tuple] = {_build_key(row) for row in previous}
    return [row for row in current if _build_key(row) not in previous_keys]


def compute_contact_changes(current: List[Dict], previous: List[Dict]) -> List[Dict]:
    """Devuelve filas con contacto nuevo o con visita agregada/cambiada.

    Reglas:
    - NO -> SI en contacto genera nota.
    - Si ya estaba en SI, pero la visita se agrega o cambia, genera nota.

    Espera claves normalizadas: codigo, contacto, visita.

    Args:
        current: Reporte actual.
        previous: Reporte anterior.

    Returns:
        Filas con cambios relevantes.
    """

    previous_by_code = {row.get("codigo"): row for row in previous}
    cambios: List[Dict] = []
    for row in current:
        codigo = row.get("codigo")
        if not codigo:
            continue
        previo = previous_by_code.get(codigo)
        contacto_actual = row.get("contacto")
        visita_actual = row.get("visita") or ""
        if not previo:
            if contacto_actual == "SI":
                cambios.append(row)
            continue
        contacto_previo = previo.get("contacto")
        visita_previa = previo.get("visita") or ""
        if contacto_previo == "NO" and contacto_actual == "SI":
            row["cambio_contacto"] = True
            cambios.append(row)
            continue
        if contacto_actual == "SI" and visita_actual != visita_previa:
            if visita_actual:
                row["cambio_visita"] = True
                cambios.append(row)
    return cambios
