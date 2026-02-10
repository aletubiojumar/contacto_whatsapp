"""Generacion de notas JSONL a partir de datos procesados."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict


def build_jsonl(entries: List[Dict], output_path: Path) -> Path:
    """Escribe un archivo JSONL con {codigo, modelo, texto}.

    Args:
        entries: Lista de notas normalizadas.
        output_path: Ruta de salida del JSONL.

    Returns:
        Ruta del archivo JSONL generado.
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return output_path
