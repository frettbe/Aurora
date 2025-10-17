"""
Configuration avancée du logging avec rotation par session.

Ce module améliore le système de logging pour :
- Créer un fichier différent à chaque session (avec date/heure)
- Garder seulement les N fichiers les plus récents
- Nettoyer automatiquement les anciens logs
"""

import glob
import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path


def setup_session_logging(
    max_files: int = 10, console_output: bool = True, log_level: int = logging.INFO
) -> Path:
    """
    Configure le logging avec fichiers par session et rotation.

    Args:
        max_files: Nombre maximum de fichiers de logs à conserver
        console_output: Afficher aussi les logs dans la console
        log_level: Niveau de logging (DEBUG, INFO, WARNING, etc.)

    Returns:
        Path: Chemin vers le fichier de log de cette session
    """
    # Importer paths après pour éviter les imports circulaires
    try:
        from ..utils.paths import logs_path

        logs_dir = logs_path()
    except ImportError:
        # Fallback si paths.py n'est pas disponible
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

    # Générer nom de fichier avec timestamp
    session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"biblio_{session_timestamp}.log"
    log_file_path = logs_dir / log_filename

    # Configuration du logger racine
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Supprimer les handlers existants pour éviter les doublons
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Formatter pour les messages
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler pour fichier
    file_handler = logging.FileHandler(log_file_path, mode="w", encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Handler pour console (optionnel)
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # Nettoyer les anciens fichiers
    cleanup_old_logs(logs_dir, max_files)

    # Log du démarrage
    logging.info(f"✅ Logging par session configuré - fichier: {log_filename}")
    logging.info(f"📁 Dossier logs: {logs_dir}")
    logging.info(f"🗂️ Conservation des {max_files} fichiers les plus récents")

    return log_file_path


def cleanup_old_logs(logs_dir: Path, max_files: int) -> None:
    """
    Supprime les anciens fichiers de logs, garde seulement les plus récents.

    Args:
        logs_dir: Dossier contenant les logs
        max_files: Nombre de fichiers à conserver
    """
    try:
        # Trouver tous les fichiers de logs avec le pattern biblio_*.log
        log_pattern = str(logs_dir / "biblio_*.log")
        log_files = glob.glob(log_pattern)

        if len(log_files) <= max_files:
            logging.debug(
                f"📊 {len(log_files)} fichiers de logs trouvés, pas de nettoyage nécessaire"
            )
            return

        # Trier par date de modification (plus récent en premier)
        log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

        # Garder seulement les max_files plus récents
        files_to_keep = log_files[:max_files]
        files_to_delete = log_files[max_files:]

        # Supprimer les anciens
        deleted_count = 0
        for old_file in files_to_delete:
            try:
                os.remove(old_file)
                deleted_count += 1
                logging.debug(f"🗑️ Ancien log supprimé: {Path(old_file).name}")
            except OSError as e:
                logging.warning(f"⚠️ Impossible de supprimer {old_file}: {e}")

        if deleted_count > 0:
            logging.info(f"🧹 Nettoyage terminé: {deleted_count} ancien(s) fichier(s) supprimé(s)")
            logging.info(f"📋 Fichiers conservés: {[Path(f).name for f in files_to_keep]}")

    except Exception as e:
        logging.warning(f"⚠️ Erreur lors du nettoyage des logs: {e}")


def get_current_session_logs(logs_dir: Path | None = None) -> list[Path]:
    """
    Retourne la liste des fichiers de logs triés par date (plus récent en premier).

    Args:
        logs_dir: Dossier des logs (optionnel, déduit automatiquement)

    Returns:
        Liste des fichiers de logs triés par date
    """
    if logs_dir is None:
        try:
            from ..utils.paths import logs_path

            logs_dir = logs_path()
        except ImportError:
            logs_dir = Path("logs")

    log_pattern = str(logs_dir / "biblio_*.log")
    log_files = glob.glob(log_pattern)

    # Trier par date de modification (plus récent en premier)
    log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

    return [Path(f) for f in log_files]


def log_session_info() -> None:
    """Log des informations sur la session actuelle."""
    import platform
    import sys

    logging.info("=" * 60)
    logging.info("🚀 NOUVELLE SESSION BIBLIO")
    logging.info("=" * 60)
    logging.info(f"🐍 Python: {sys.version}")
    logging.info(f"💻 Système: {platform.system()} {platform.release()}")
    logging.info(f"📅 Session: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info("=" * 60)


# Fonction de compatibilité avec l'ancien système
def setup_app_logging(console_output: bool = True, max_log_files: int = 10) -> Path:
    """
    Point d'entrée principal - compatible avec l'ancien système.

    Args:
        console_output: Afficher les logs dans la console
        max_log_files: Nombre de fichiers de logs à conserver

    Returns:
        Chemin vers le fichier de log de cette session
    """
    log_file = setup_session_logging(
        max_files=max_log_files, console_output=console_output, log_level=logging.INFO
    )

    # Log des infos de session
    log_session_info()

    return log_file
