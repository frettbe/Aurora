"""
Service de gestion de l'internationalisation (i18n).

Ce module fournit un système simple mais efficace pour charger et utiliser
des traductions à partir de fichiers YAML. Il maintient un état global pour
la langue courante et les traductions chargées.

Fonctions principales :
- set_language(lang): Charge le fichier de traduction pour la langue spécifiée.
- translate(key, **kwargs): Récupère une chaîne traduite par sa clé et la formate.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

# Instance globale (Singleton pattern) – assure-toi que cette ligne est là !
_translation_service: TranslationService | None = None

logger = logging.getLogger(__name__)


class TranslationService:
    """Service de gestion des traductions de l'application.

    Gère le chargement des fichiers YAML pour différentes langues,
    et fournit une fonction de traduction avec support pour clés nested.
    Utilise un pattern singleton pour une instance unique.
    """

    def __init__(self) -> None:
        self.current_language: str = "fr"  # Langue par défaut
        self.translations: dict[str, dict[str, Any]] = {}
        self.load_language("fr")  # Charge auto la langue par défaut à l'init

    def load_language(self, language_code: str) -> bool:
        """Charge un fichier de langue spécifique depuis le dossier 'lang'."""
        lang_file = Path(__file__).parent.parent.parent / "lang" / f"{language_code}.yaml"
        try:
            if lang_file.exists():
                with open(lang_file, encoding="utf-8") as f:
                    self.translations[language_code] = yaml.safe_load(f) or {}
                return True
            else:
                logger.warning("Fichier de langue manquant : %s", lang_file)
                return False
        except Exception as e:
            logger.error("Erreur lors du chargement du fichier de langue %s: %s", lang_file, e)
            return False

    def set_language(self, language_code: str) -> None:
        """Définit la langue courante et la charge si nécessaire."""
        if language_code not in self.translations:
            self.load_language(language_code)
        if language_code in self.translations:
            self.current_language = language_code
        else:
            logger.error("Tentative de passer à une langue non chargée : %s", language_code)

    def translate(self, key: str, **kwargs: Any) -> str:
        """Traduit une clé en utilisant le fichier de langue courant.

        Supporte les clés nested (ex: 'menu.file.new_book') et le formattage
        avec kwargs. Fallback sur la key si non trouvée.

        Args:
            key: Clé de traduction (ex: 'menu.file.new_book').
            **kwargs: Valeurs pour formattage (ex: .format(name='Bob')).

        Returns:
            Chaîne traduite.
        """
        lang_data = self.translations.get(self.current_language)
        if not lang_data:
            return key  # Fallback si la langue n'est pas chargée

        # Gère les clés imbriquées (ex: "dialogs.buttons.ok")
        keys = key.split(".")
        value = lang_data
        try:
            for k in keys:
                value = value[k]
        except (KeyError, TypeError):
            return key  # Fallback si la clé n'est pas trouvée

        if isinstance(value, str):
            return value.format(**kwargs) if kwargs else value
        return str(value)


def get_translation_service() -> TranslationService:
    """Retourne l'instance unique du service de traduction."""
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service


def set_language(language_code: str) -> None:
    """Raccourci pour changer la langue globale."""
    get_translation_service().set_language(language_code)


def translate(key: str, **kwargs: Any) -> str:
    """Raccourci pour traduire une clé."""
    return get_translation_service().translate(key, **kwargs)
