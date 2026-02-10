"""Genera notas JSONL a partir de los reportes de Peritoline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.build_notas import build_jsonl  # noqa: E402
from processing.diff import compute_contact_changes  # noqa: E402
from processing.excel_parser import normalize_text, parse_report  # noqa: E402
from utils.logging_utils import get_logger, setup_logging  # noqa: E402


def _build_text(visita: str) -> str:
    """Construye el texto de la nota segun la visita.

    Args:
        visita: Fecha de visita en formato libre.

    Returns:
        Texto final de la nota.
    """

    if visita:
        return f"Se ha concertado intervencion para fecha {visita}"
    return "Se ha contactado con el asegurado"


def _parse_peritos(value: str) -> list[str]:
    """Convierte una lista separada por comas en peritos normalizados.

    Args:
        value: Cadena con nombres separados por coma.

    Returns:
        Lista de peritos normalizados.
    """

    if not value:
        return []
    return [normalize_text(item) for item in value.split(",") if item.strip()]


def _match_perito(cell_value: str, peritos: set[str]) -> bool:
    """Verifica si la celda contiene alguno de los peritos objetivo.

    Args:
        cell_value: Texto de peritos en el Excel.
        peritos: Conjunto de peritos normalizados.

    Returns:
        True si hay coincidencia, False si no.
    """

    if not peritos:
        return True
    normalized = normalize_text(cell_value)
    if normalized in peritos:
        return True
    parts = [part.strip() for part in cell_value.split("-") if part.strip()]
    for part in parts:
        if normalize_text(part) in peritos:
            return True
    return False


def main() -> None:
    """Ejecuta la generacion de JSONL desde los reportes.

    Returns:
        None.
    """

    setup_logging()
    logger = get_logger(tarea="peritoline_allianz")
    parser = argparse.ArgumentParser(
        description="Genera data/notas_allianz.jsonl comparando reportes de Peritoline."
    )
    parser.add_argument(
        "--latest",
        default="data/peritoline/raw/peritoline_report_latest.xlsx",
        help="Ruta del ultimo reporte descargado.",
    )
    parser.add_argument(
        "--previous",
        default="data/peritoline/raw/peritoline_report_previous.xlsx",
        help="Ruta del reporte anterior.",
    )
    parser.add_argument(
        "--output",
        default="data/notas_allianz.jsonl",
        help="Ruta de salida del JSONL.",
    )
    parser.add_argument(
        "--modelo",
        required=True,
        help="Codigo de modelo de nota a usar (ej: 241).",
    )
    parser.add_argument(
        "--perito",
        default="JESUS M. VIDAL",
        help="Nombre del perito a filtrar.",
    )
    parser.add_argument(
        "--peritos",
        default="",
        help="Lista de peritos separados por coma para filtrar.",
    )
    args = parser.parse_args()

    latest_path = Path(args.latest)
    previous_path = Path(args.previous)
    output_path = Path(args.output)

    if not latest_path.exists():
        raise SystemExit(f"No existe el reporte: {latest_path}")

    current = parse_report(latest_path)
    previous = parse_report(previous_path) if previous_path.exists() else []

    cambios = compute_contact_changes(current, previous)
    peritos = set(_parse_peritos(args.peritos))
    if args.perito:
        peritos.add(normalize_text(args.perito))
    filtrados = [
        row for row in cambios if _match_perito(row.get("perito", ""), peritos)
    ]

    notas = [
        {
            "codigo": row["codigo"],
            "modelo": args.modelo,
            "texto": _build_text(row.get("visita", "")),
        }
        for row in filtrados
    ]

    build_jsonl(notas, output_path)
    logger.info("Notas generadas: %s (%s entradas)", output_path, len(notas))


if __name__ == "__main__":
    main()
