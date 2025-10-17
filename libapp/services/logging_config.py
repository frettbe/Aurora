"""Configuration centralisée du logging pour l'application Biblio."""

import logging
import logging.handlers

from ..utils.paths import logs_path


def setup_app_logging(log_level: str = "INFO", console_output: bool = False) -> logging.Logger:
    """Configure le logging centralisé pour toute l'app Biblio.

    Args:
        log_level: Niveau de log (DEBUG, INFO, WARNING, ERROR)
        console_output: Si True, affiche aussi en console (pour debug)

    Returns:
        Logger configuré
    """
    # Dossier logs à la racine du projet
    log_dir = logs_path()
    log_dir.mkdir(exist_ok=True)

    # Configuration du root logger
    logger = logging.getLogger()
    logger.handlers.clear()  # Nettoie les handlers existants
    logger.setLevel(getattr(logging, log_level.upper()))

    # Handler fichier avec rotation (10MB, 5 fichiers)
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "biblio.log",
        maxBytes=10_000_000,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )

    # Format détaillé avec module
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Handler console optionnel (pour développement)
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    logger.info("✅ Logging centralisé configuré - fichier: %s", log_dir / "biblio.log")
    return logger
