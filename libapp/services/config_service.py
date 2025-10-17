"""
Service de gestion de la configuration statique de l'application.

Ce module centralise les configurations qui ne sont pas destinées à être
modifiées par l'utilisateur via l'interface, mais qui sont importantes
pour le fonctionnement de certains services (comme l'import/export).

L'idée est d'avoir une "source de vérité" unique pour ces paramètres.
"""

import json
import logging
from dataclasses import asdict, dataclass

from libapp.utils.paths import user_data_dir

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AppConfig:
    """Holds the application's user-configurable settings."""

    start_view: str = "search"  # "dashboard" or "search"
    theme: str = "system"  # "system", "light", "dark"
    database_path: str | None = None


def get_config_path():
    return user_data_dir() / "config.json"


def load_config() -> AppConfig:
    """Loads config from file, or returns defaults if it doesn't exist or is invalid."""
    config_path = get_config_path()
    if not config_path.exists():
        logger.info("Config file not found. Using default configuration.")
        return AppConfig()

    try:
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
            # This allows adding new config keys with default values in future versions
            current_config = AppConfig(**data)
            return current_config
    except (OSError, json.JSONDecodeError, TypeError) as e:
        logger.error(
            f"Could not read, parse, or validate config file at {config_path}: {e}. Using defaults."
        )
        return AppConfig()


def save_config(config: AppConfig) -> None:
    """Saves the given configuration object to the file."""
    config_path = get_config_path()
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(asdict(config), f, indent=4)
        logger.info(f"Configuration saved to {config_path}")
    except OSError as e:
        logger.error(f"Could not write to config file at {config_path}: {e}")
