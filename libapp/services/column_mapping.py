"""
Service intelligent de suggestion de mapping de colonnes.
Utilise des algorithmes de similarité pour proposer automatiquement
le mapping entre colonnes Excel et champs base de données.
"""

from __future__ import annotations

import json
import logging
import re
from difflib import SequenceMatcher
from pathlib import Path

# Dictionnaire de mots-clés par champ de base de données
DEFAULT_FIELD_KEYWORDS = {
    "title": ["titre", "title", "book", "livre", "nom", "name", "ouvrage", "designation"],
    "author": ["auteur", "author", "auteur(s)", "authors", "écrivain", "writer", "creator"],
    "isbn": ["isbn", "isbn13", "isbn10", "ean", "code_barre", "barcode", "code"],
    "year": ["année", "year", "date", "an", "annee", "edition", "parution", "published"],
    "publisher": ["éditeur", "publisher", "maison", "edition", "editeur", "press"],
    "code": ["code", "ref", "référence", "reference", "id", "numéro", "num", "identifier"],
    "volume": ["volume", "tome", "vol", "number", "numero", "n°", "part"],
    "fund": ["fonds", "fund", "collection", "série", "serie", "series"],
    "copies_total": ["exemplaires", "copies", "total", "quantité", "qte", "quantity", "stock"],
    "copies_available": ["disponibles", "available", "libre", "dispo", "free", "libres"],
}


def load_field_keywords() -> dict[str, list[str]]:
    """Charge les mots-clés depuis JSON avec fallback."""
    json_path = Path(__file__).parent / "field_keywords.json"

    try:
        if json_path.exists():
            with open(json_path, encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logging.warning(f"Impossible de charger field_keywords.json: {e}")

    return DEFAULT_FIELD_KEYWORDS


# Charge au moment de l'import du module
FIELD_KEYWORDS = load_field_keywords()


def calculate_similarity_score(field_keywords: list[str], column_name: str) -> float:
    """
    Calcule un score de similarité entre une colonne et un champ.

    Args:
        field_keywords: Liste des mots-clés pour le champ
        column_name: Nom de la colonne à analyser

    Returns:
        Score entre 0.0 et 1.0 (1.0 = match parfait)
    """
    if not column_name:
        return 0.0

    column_clean = normalize_text(column_name)

    # 1. Match exact (score parfait)
    if column_clean in [normalize_text(kw) for kw in field_keywords]:
        return 1.0

    # 2. Match partiel (contient le mot-clé)
    max_partial_score = 0.0
    for keyword in field_keywords:
        keyword_clean = normalize_text(keyword)

        if keyword_clean in column_clean or column_clean in keyword_clean:
            match_ratio = len(keyword_clean) / max(len(column_clean), len(keyword_clean))
            partial_score = 0.7 * match_ratio
            max_partial_score = max(max_partial_score, partial_score)

    # 3. Similarité approximative (Levenshtein-like)
    max_fuzzy_score = 0.0
    for keyword in field_keywords:
        keyword_clean = normalize_text(keyword)
        fuzzy_ratio = SequenceMatcher(None, column_clean, keyword_clean).ratio()

        if fuzzy_ratio > 0.6:  # Seuil pour éviter les faux positifs
            fuzzy_score = 0.4 * fuzzy_ratio
            max_fuzzy_score = max(max_fuzzy_score, fuzzy_score)

    return max(max_partial_score, max_fuzzy_score)


def normalize_text(text: str) -> str:
    """Normalise un texte pour la comparaison."""
    if not text:
        return ""

    text = text.lower().strip()

    # Suppression accents
    accent_map = {
        "é": "e",
        "è": "e",
        "ê": "e",
        "ë": "e",
        "à": "a",
        "â": "a",
        "ä": "a",
        "ù": "u",
        "û": "u",
        "ü": "u",
        "ô": "o",
        "ö": "o",
        "î": "i",
        "ï": "i",
        "ç": "c",
    }

    for accented, plain in accent_map.items():
        text = text.replace(accented, plain)

    # Suppression caractères spéciaux
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def suggest_column_mapping(column_names: list[str], db_fields: list[str] = None) -> dict[str, str]:
    """
    Suggère un mapping automatique entre colonnes Excel et champs DB.

    Args:
        column_names: Liste des noms de colonnes du fichier Excel
        db_fields: Liste des champs de base (optionnel)

    Returns:
        Dictionnaire {field_name: suggested_column_name}
    """
    if db_fields is None:
        db_fields = list(FIELD_KEYWORDS.keys())

    suggestions = {}
    used_columns = set()

    for field in db_fields:
        if field not in FIELD_KEYWORDS:
            continue

        field_keywords = FIELD_KEYWORDS[field]
        best_score = 0.0
        best_column = None

        for column in column_names:
            if column in used_columns:
                continue

            score = calculate_similarity_score(field_keywords, column)

            if score > best_score and score > 0.3:  # Seuil minimum
                best_score = score
                best_column = column

        if best_column:
            suggestions[field] = best_column
            used_columns.add(best_column)

    return suggestions
