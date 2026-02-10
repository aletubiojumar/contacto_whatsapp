"""Parseo del Excel de Peritoline a una estructura normalizada."""

from __future__ import annotations

from pathlib import Path
from typing import List, Dict
import unicodedata

import pandas as pd


def normalize_text(value: object) -> str:
    """Normaliza texto para comparaciones (mayusculas, sin tildes).

    Args:
        value: Texto bruto.

    Returns:
        Texto normalizado.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.upper()


def _normalize_codigo(value: object) -> str:
    """Normaliza el codigo de siniestro evitando sufijos .0.

    Args:
        value: Codigo de siniestro.

    Returns:
        Codigo normalizado.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip()
    if text.endswith(".0") and text.replace(".", "", 1).isdigit():
        return text[:-2]
    return text


def _format_visita(value: object) -> str:
    """Formatea la fecha de visita a dd/mm/yyyy si es posible.

    Args:
        value: Valor crudo de visita.

    Returns:
        Fecha formateada o texto original.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return ""
        return value.strftime("%d/%m/%Y")
    parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)
    if not pd.isna(parsed):
        return parsed.strftime("%d/%m/%Y")
    return str(value).strip()


def parse_report(path: Path) -> List[Dict]:
    """Lee el Excel y devuelve filas normalizadas.

    Columnas esperadas: Peritos, C, Siniestro, Visita.

    Args:
        path: Ruta del archivo Excel.

    Returns:
        Lista de filas normalizadas.
    """

    df = pd.read_excel(path)
    required = ["Peritos", "C", "Siniestro", "Visita"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en el Excel: {', '.join(missing)}")

    records: List[Dict] = []
    for _, row in df.iterrows():
        codigo = _normalize_codigo(row["Siniestro"])
        if not codigo:
            continue
        records.append(
            {
                "codigo": codigo,
                "perito": normalize_text(row["Peritos"]),
                "contacto": normalize_text(row["C"]),
                "visita": _format_visita(row["Visita"]),
            }
        )
    return records
