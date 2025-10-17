"""
Service pour la gestion des sauvegardes et des restaurations.

Ce module fournit des fonctions de haut niveau pour créer une copie de
sécurité de la base de données de l'application et, à l'avenir, pour la
restaurer à partir d'un fichier de sauvegarde.
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path

from ..utils.paths import db_path, user_data_dir

# Configure un logger spécifique à ce module pour un meilleur suivi
logger = logging.getLogger(__name__)


class BackupError(Exception):
    """
    Exception personnalisée levée pour toute erreur durant le processus
    de sauvegarde ou de restauration.
    """

    pass


def create_backup(backup_folder: Path | None = None) -> Path:
    """
    Crée une copie de sauvegarde de la base de données SQLite.

    Cette fonction localise la base de données principale, détermine un
    dossier de destination (soit celui fourni, soit un dossier par défaut
    'backups'), et y copie le fichier de la base de données en lui ajoutant
    un horodatage pour garantir son unicité.

    Args:
        backup_folder:
            Le chemin vers le dossier où la sauvegarde doit être enregistrée.
            Si non spécifié (None), le dossier `backups` dans le répertoire
            des données utilisateur sera utilisé.

    Returns:
        Le chemin complet vers le fichier de sauvegarde nouvellement créé.

    Raises:
        BackupError: Si le fichier de la base de données source n'est pas
                     trouvé ou si une erreur de copie se produit.
    """
    source_db = db_path()
    logger.debug("Chemin de la base de données source : %s", source_db)

    if not source_db.exists():
        msg = f"La base de données source n'a pas été trouvée à l'emplacement : {source_db}"
        logger.error(msg)
        raise BackupError(msg)

    # Détermine le dossier de destination pour la sauvegarde
    if backup_folder:
        dest_dir = backup_folder
    else:
        dest_dir = user_data_dir() / "backups"
    logger.debug("Dossier de destination pour la sauvegarde : %s", dest_dir)

    # Crée le dossier de destination s'il n'existe pas
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Construit un nom de fichier unique basé sur la date et l'heure actuelles
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"codex_backup_{timestamp}.db"
    dest_path = dest_dir / backup_filename
    logger.info("Création de la sauvegarde : %s", dest_path)

    try:
        # Copie le fichier et ses métadonnées (permissions, etc.)
        shutil.copy2(source_db, dest_path)
        logger.info("Sauvegarde de la base de données créée avec succès.")
        return dest_path
    except OSError as e:
        logger.error("Erreur d'E/S lors de la copie du fichier de sauvegarde : %s", e)
        raise BackupError(f"Échec de la création de la sauvegarde : {e}") from e
