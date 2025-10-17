"""Gestion des préférences utilisateur.

Ce module gère la sauvegarde et le chargement des préférences de l'application
dans un fichier JSON local. Il utilise un `dataclass` pour une structure
claire et une sérialisation/désérialisation robuste.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from typing import Any

from ..utils.paths import user_config_file


@dataclass
class Preferences:
    """Structure contenant toutes les préférences de l'application."""

    # Préférences générales
    language: str = "fr"
    startup_view: str = "books"
    theme: str = "system"
    remember_window_geometry: bool = True
    main_window_geometry: bytes | None = None

    # Préférences spécifiques aux modules
    import_last_directory: str | None = None
    import_last_mapping: dict[str, str] = field(default_factory=dict)

    # États des vues
    books_view_state: dict[str, Any] = field(default_factory=dict)
    members_view_state: dict[str, Any] = field(default_factory=dict)
    loans_view_state: dict[str, Any] = field(default_factory=dict)

    # Colonnes visibles
    books_visible_columns: list[str] = field(
        default_factory=lambda: [
            "id",
            "code",
            "title",
            "author",
            "year",
            "isbn",
            "publisher",
            "fund",
            "available",
        ]
    )
    members_visible_columns: list[str] = field(
        default_factory=lambda: [
            "id",
            "member_number",
            "first_name",
            "last_name",
            "status",
            "is_active",
        ]
    )
    loans_visible_columns: list[str] = field(
        default_factory=lambda: [
            "id",
            "book_title",
            "member_name",
            "loan_date",
            "due_date",
            "return_date",
        ]
    )

    # Exports metadata
    export_include_date: bool = True
    export_include_count: bool = True
    export_include_custom_message: bool = False
    export_last_custom_message: str = ""
    export_last_format: str = "xlsx"
    export_last_columns_books: list[str] = field(default_factory=list)
    export_last_columns_members: list[str] = field(default_factory=list)

    # Library config
    library_name: str = ""
    library_name_enabled: bool = False

    # App name
    app_name: str = "Aurora"
    app_name_custom: bool = False

    # Alertes et comportement
    show_overdue_alert_on_startup: bool = True

    # Politique de prêt simplifiée (durée fixe pour tous)
    default_loan_days: int = 14

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Preferences:
        """Crée une instance de Preferences à partir d'un dictionnaire."""
        known_keys = cls.__annotations__.keys()
        filtered_data = {k: v for k, v in data.items() if k in known_keys}
        return cls(**filtered_data)


def load_preferences() -> Preferences:
    """Charge les préférences depuis le fichier de configuration JSON."""
    config_file = user_config_file()
    if not config_file.exists():
        logging.info("Aucun fichier de préférences trouvé, utilisation des valeurs par défaut.")
        return Preferences()

    try:
        with config_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Gestion sécurisée de la géométrie
        if "main_window_geometry" in data and data["main_window_geometry"]:
            try:
                import base64

                from PySide6.QtCore import QByteArray

                geom_str = data["main_window_geometry"]
                geom_bytes = base64.b64decode(geom_str.encode("ascii"))
                data["main_window_geometry"] = QByteArray(geom_bytes)
            except Exception as geom_error:
                logging.warning("Erreur décodage géométrie: %s. Géométrie ignorée.", geom_error)
                data["main_window_geometry"] = None

        logging.info("Préférences chargées depuis %s", config_file)
        return Preferences.from_dict(data)

    except Exception as e:
        logging.warning(
            "Erreur lors du chargement des préférences: %s. Utilisation des valeurs par défaut.", e
        )
        return Preferences()


def save_preferences(prefs: Preferences) -> bool:
    """Sauvegarde les préférences dans le fichier de configuration JSON.

    Args:
        prefs: Instance de Preferences à sauvegarder.

    Returns:
        True si la sauvegarde a réussi, False sinon.
    """
    try:
        config_file = user_config_file()
        config_file.parent.mkdir(parents=True, exist_ok=True)

        data_to_save = asdict(prefs)

        # Gestion sécurisée de la géométrie
        if "main_window_geometry" in data_to_save and data_to_save["main_window_geometry"]:
            try:
                import base64

                geom = data_to_save["main_window_geometry"]
                data_to_save["main_window_geometry"] = base64.b64encode(bytes(geom)).decode("ascii")
            except Exception as geom_error:
                logging.warning("Erreur encodage géométrie: %s. Géométrie non sauvée.", geom_error)
                data_to_save["main_window_geometry"] = None

        with config_file.open("w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=4)

        logging.info("Préférences sauvegardées dans %s", config_file)
        return True

    except Exception as e:
        logging.error("Erreur lors de la sauvegarde des préférences: %s", e)
        return False
