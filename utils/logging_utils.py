"""Configuracion central de logging."""

from __future__ import annotations

import logging
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


class _ContextFilter(logging.Filter):
    """Garantiza campos requeridos para el formato."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Completa los campos extra del log.

        Args:
            record: Registro de logging a enriquecer.

        Returns:
            True si el registro debe procesarse.
        """

        if not hasattr(record, "siniestro"):
            record.siniestro = "sin_codigo"
        if not hasattr(record, "tarea"):
            record.tarea = "pendiente"
        return True


def setup_logging(log_dir: str | Path = "/tmp/logs", log_file: str = "app.log") -> Path:

    """Inicializa logging a consola y archivo con rotacion diaria.

    Args:
        log_dir: Carpeta base para los logs.
        log_file: Nombre del archivo principal.

    Returns:
        Ruta final del archivo de log principal.
    """

    if logging.getLogger().handlers:
        return Path(log_dir) / log_file

    log_dir_env = os.getenv("LOG_DIR")
    backup_env = os.getenv("LOG_BACKUP_COUNT")
    if log_dir_env:
        log_dir = log_dir_env
    backup_count = int(backup_env) if backup_env and backup_env.isdigit() else 30

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    full_path = log_path / log_file

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | Siniestro: %(siniestro)s | "
        "Tarea: %(tarea)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = TimedRotatingFileHandler(
        full_path, when="midnight", backupCount=backup_count, encoding="utf-8"
    )
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(_ContextFilter())

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(_ContextFilter())

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(stream_handler)

    return full_path


def get_logger(
    siniestro: str | None = None, tarea: str | None = None, name: str = "app"
) -> logging.LoggerAdapter:
    """Crea un logger con contexto de siniestro y tarea.

    Args:
        siniestro: Codigo del siniestro.
        tarea: Nombre del paso/tarea.
        name: Nombre del logger base.

    Returns:
        LoggerAdapter con el contexto inyectado.
    """

    extra = {
        "siniestro": siniestro or "sin_codigo",
        "tarea": tarea or "pendiente",
    }
    return logging.LoggerAdapter(logging.getLogger(name), extra)
