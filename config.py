"""Funciones de configuracion utilizadas por todo el flujo de automatizacion."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Dict

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - paquete opcional
    load_dotenv = None

if load_dotenv:
    load_dotenv()


@dataclass
class AppConfig:
    """Agrupa parametros compartidos por la CLI, los Page Objects y el workflow."""

    base_url: str
    username: str
    password: str
    headless: bool = False
    navigation_timeout_ms: int = 30_000
    upload_timeout_ms: int = 120_000
    slow_mo_ms: int = 250
    keep_browser_open: bool = True
    min_action_delay_s: float = 0.6
    max_action_delay_s: float = 2.4
    peritoline_login_url: str = ""
    peritoline_username: str = ""
    peritoline_password: str = ""


def _resolve(
    overrides: Dict[str, Any],
    field_name: str,
    env_key: str,
    default: Any,
    caster: Callable[[str], Any] | None = None,
) -> Any:
    """Devuelve el valor correspondiente al campo indicado.

    Precedencia de valores:
    1) overrides (pensado para pruebas)
    2) variable de entorno
    3) valor por defecto.

    Args:
        overrides: Valores que sobrescriben el entorno.
        field_name: Nombre del campo destino.
        env_key: Variable de entorno a consultar.
        default: Valor por defecto.
        caster: Funcion opcional para convertir el valor.

    Returns:
        Valor resuelto para el campo.
    """

    if field_name in overrides:
        return overrides[field_name]

    env_value = os.getenv(env_key)
    if env_value is not None:
        return caster(env_value) if caster else env_value

    return default


def _to_bool(value: str) -> bool:
    """Convierte cadenas tipo 'true/1/on' en booleanos.

    Args:
        value: Cadena a convertir.

    Returns:
        Booleano equivalente.
    """

    return value.strip().lower() in {"1", "true", "yes", "on"}


def _to_int(value: str, default: int) -> int:
    """Convierte el valor recibido en entero o devuelve el valor por defecto.

    Args:
        value: Cadena a convertir.
        default: Valor por defecto si falla la conversion.

    Returns:
        Entero resultante o valor por defecto.
    """

    try:
        return int(value)
    except ValueError:
        return default


def _to_float(value: str, default: float) -> float:
    """Convierte el valor recibido en flotante o devuelve el valor por defecto.

    Args:
        value: Cadena a convertir.
        default: Valor por defecto si falla la conversion.

    Returns:
        Flotante resultante o valor por defecto.
    """

    try:
        return float(value)
    except ValueError:
        return default


def load_config(overrides: Dict[str, Any] | None = None) -> AppConfig:
    """Construye una instancia de AppConfig lista para consumirse en el workflow.

    En un despliegue real se alimenta con variables de entorno, banderas CLI
    o servicios de secretos. El parametro overrides facilita pruebas unitarias.

    Args:
        overrides: Diccionario opcional con valores forzados.

    Returns:
        Instancia de AppConfig con los valores resueltos.
    """

    overrides = overrides or {}

    base_settings = {
        "base_url": _resolve(
            overrides,
            "base_url",
            "APP_BASE_URL",
            "https://portal-ejemplo.com/login",
        ),
        "username": _resolve(overrides, "username", "APP_USERNAME", "USUARIO"),
        "password": _resolve(overrides, "password", "APP_PASSWORD", "SECRETO"),
        "headless": _resolve(
            overrides,
            "headless",
            "APP_HEADLESS",
            False,
            caster=_to_bool,
        ),
        "slow_mo_ms": _resolve(
            overrides,
            "slow_mo_ms",
            "APP_SLOW_MO_MS",
            250,
            caster=lambda value, default=250: _to_int(value, default),
        ),
        "keep_browser_open": _resolve(
            overrides,
            "keep_browser_open",
            "APP_KEEP_BROWSER_OPEN",
            True,
            caster=_to_bool,
        ),
        "min_action_delay_s": _resolve(
            overrides,
            "min_action_delay_s",
            "APP_MIN_ACTION_DELAY_S",
            0.6,
            caster=lambda value, default=0.6: _to_float(value, default),
        ),
        "max_action_delay_s": _resolve(
            overrides,
            "max_action_delay_s",
            "APP_MAX_ACTION_DELAY_S",
            2.4,
            caster=lambda value, default=2.4: _to_float(value, default),
        ),
        "navigation_timeout_ms": _resolve(
            overrides,
            "navigation_timeout_ms",
            "APP_NAV_TIMEOUT_MS",
            30_000,
            caster=lambda value, default=30_000: _to_int(value, default),
        ),
        "peritoline_login_url": _resolve(
            overrides,
            "peritoline_login_url",
            "PERITOLINE_LOGIN_URL",
            "",
        ),
        "peritoline_username": _resolve(
            overrides,
            "peritoline_username",
            "PERITOLINE_USERNAME",
            "",
        ),
        "peritoline_password": _resolve(
            overrides,
            "peritoline_password",
            "PERITOLINE_PASSWORD",
            "",
        ),
        "upload_timeout_ms": _resolve(
            overrides,
            "upload_timeout_ms",
            "APP_SUBMIT_TIMEOUT_MS",
            120_000,
            caster=lambda value, default=120_000: _to_int(value, default),
        ),
    }

    min_delay = base_settings["min_action_delay_s"]
    max_delay = base_settings["max_action_delay_s"]
    if min_delay > max_delay:
        min_delay, max_delay = max_delay, min_delay
        base_settings["min_action_delay_s"] = min_delay
        base_settings["max_action_delay_s"] = max_delay

    return AppConfig(**base_settings)
