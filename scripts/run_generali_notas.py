"""Runner para ejecutar notas de Generali desde JSONL."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import load_config  # noqa: E402
from generali.workflow import run_generali_in_session  # noqa: E402
from utils.logging_utils import get_logger, setup_logging  # noqa: E402


def _load_notas_generali(path: Path) -> List[Dict[str, str]]:
    """Lee el archivo JSONL de Generali.

    Args:
        path: Ruta al JSONL.

    Returns:
        Lista de notas con codigo, fecha_visita y texto.
    """

    notas: List[Dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig") as fh:
        for line_number, line in enumerate(fh, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Linea {line_number}: JSON invalido ({exc})") from exc

            for key in ("codigo", "texto"):
                if key not in payload or not payload[key]:
                    raise ValueError(
                        f"Linea {line_number}: falta el campo obligatorio '{key}'."
                    )

            notas.append(
                {
                    "codigo": payload["codigo"],
                    "fecha_visita": payload.get("fecha_visita", ""),
                    "texto": payload["texto"],
                }
            )

    if not notas:
        raise ValueError("El archivo JSONL no contiene ninguna nota valida.")
    return notas


def main() -> None:
    """Ejecuta el runner de notas Generali.

    Returns:
        None.
    """

    setup_logging()
    logger = get_logger(tarea="generali_notas")
    parser = argparse.ArgumentParser(
        description="Ejecuta notas de Generali leyendo un JSONL."
    )
    parser.add_argument(
        "--notas-jsonl",
        default="data/notas_generali.jsonl",
        help="Ruta al JSONL de Generali.",
    )
    parser.add_argument(
        "--skip-guardar",
        action="store_true",
        help="Omite el click en GUARDAR al final de cada siniestro.",
    )
    args = parser.parse_args()

    notas = _load_notas_generali(Path(args.notas_jsonl))
    logger.info("Iniciando notas Generali (%s entradas)", len(notas))
    config = load_config()
    run_generali_in_session(config, notas, skip_guardar=args.skip_guardar)
    logger.info("Notas Generali finalizadas")


if __name__ == "__main__":
    main()
