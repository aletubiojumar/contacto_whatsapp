"""Rutinas que introducen pausas aleatorias para simular interaccion humana."""

from __future__ import annotations

import random
import time
from typing import Optional

from config import AppConfig
from utils.logging_utils import get_logger


def human_delay(
    config: AppConfig, motivo: Optional[str] = None, siniestro: Optional[str] = None
) -> None:
    """Espera un intervalo aleatorio entre min_action_delay_s y max_action_delay_s.

    Args:
        config: Configuracion de tiempos de espera.
        motivo: Descripcion breve del paso.
        siniestro: Codigo de siniestro para trazabilidad.

    Returns:
        None.
    """

    inicio = config.min_action_delay_s
    fin = config.max_action_delay_s
    pausa = random.uniform(inicio, fin)
    logger = get_logger(siniestro=siniestro, tarea=motivo or "espera_humana")
    logger.info("Pausa humana de %.2fs", pausa)
    time.sleep(pausa)
