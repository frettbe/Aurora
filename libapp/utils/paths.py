"""
Gestion centralisée des chemins de fichiers de l'application.

Ce module fournit des fonctions pour obtenir les chemins d'accès aux
répertoires et fichiers de données de l'application de manière
fiable et multi-plateforme, en utilisant le dossier de données de
l'utilisateur (ex: %APPDATA% sur Windows, ~/.local/share sur Linux).
"""

from __future__ import annotations

import os
from pathlib import Path

_APP_NAME = "Aurora-Community"
_AUTHOR = "6f4Software"


def _get_app_dir(roaming: bool = False) -> Path:
    """
    Détermine le dossier de données de l'application en fonction de l'OS.

    Args:
        roaming (bool): Sur Windows, détermine s'il faut utiliser le profil
                        itinérant (Roaming) ou local. Inutilisé sur les autres OS.

    Returns:
        Path: Le chemin vers le dossier de données de l'application.
    """
    if os.name == "nt":
        key = "APPDATA" if roaming else "LOCALAPPDATA"
        base = Path(
            os.environ.get(key, Path.home() / "AppData" / ("Roaming" if roaming else "Local"))
        )
    else:
        # Suit la spécification XDG pour Linux
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    return base / _AUTHOR / _APP_NAME


def user_data_dir() -> Path:
    """Retourne le chemin vers le dossier principal des données utilisateur."""
    p = _get_app_dir(roaming=False)
    p.mkdir(parents=True, exist_ok=True)
    return p


def user_config_file() -> Path:
    """Retourne le chemin vers le fichier de configuration JSON."""
    return user_data_dir() / "preferences.json"


def db_path() -> Path:
    """Retourne le chemin vers le fichier de la base de données SQLite."""
    p = user_data_dir() / "db" / "library.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def translations_path() -> Path:
    """Retourne le chemin vers le dossier contenant les fichiers de traduction."""
    return Path.cwd() / "libapp" / "translations"


def logs_path() -> Path:
    """Retourne le chemin vers le dossier destiné à stocker les logs."""
    p = user_data_dir() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def user_covers_dir() -> Path:
    """Retourne le dossier de stockage des couvertures de livres.

    Returns:
        Path: Chemin vers le dossier covers/ (créé automatiquement si inexistant)
    """
    covers_dir = user_data_dir() / "covers"
    covers_dir.mkdir(parents=True, exist_ok=True)
    return covers_dir


def user_profile_images_dir() -> Path:
    """Retourne le dossier de stockage des photos de profil des membres.

    Returns:
        Path: Chemin vers le dossier profile_images/ (créé automatiquement si inexistant)
    """
    profile_dir = user_data_dir() / "profile_images"
    profile_dir.mkdir(parents=True, exist_ok=True)
    return profile_dir
