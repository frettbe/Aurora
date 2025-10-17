"""
Boîte à outils de fonctions utilitaires partagées.

Ce module contient de petites fonctions pures et réutilisables qui n'ont
pas leur place dans un service métier spécifique mais qui sont utiles
à plusieurs endroits de l'application.
"""

from __future__ import annotations


def clean_author(author_string: str | None) -> str:
    """
    Nettoie et formate une chaîne de caractères représentant un ou plusieurs auteurs.

    Enlève les espaces superflus et pourrait, à l'avenir, gérer des
    logiques plus complexes (comme inverser "Nom, Prénom").

    Args:
        author_string: La chaîne de caractères à nettoyer.

    Returns:
        La chaîne de caractères nettoyée.
    """
    if not author_string:
        return ""
    return author_string.strip()


def normalize_isbn(isbn: str) -> str | None:
    """
    Normalise un ISBN en supprimant les tirets, espaces et caractères non-numériques.

    Args:
        isbn: ISBN à normaliser (peut contenir tirets, espaces, etc.)

    Returns:
        ISBN normalisé (chiffres seuls) ou None si invalide
    """
    if not isbn or isbn == "None":
        return None

    # Supprimer tous les caractères non-numériques sauf X (pour ISBN-10)
    normalized = "".join(c for c in isbn.upper() if c.isdigit() or c == "X")

    # Vérifier longueur (ISBN-10 = 10 chars, ISBN-13 = 13 chars)
    if len(normalized) in (10, 13):
        return normalized

    return None


def validate_isbn(isbn: str) -> bool:
    """
    Valide un ISBN-10 ou ISBN-13.

    Args:
        isbn: ISBN à valider

    Returns:
        True si l'ISBN est valide, False sinon
    """
    normalized = normalize_isbn(isbn)
    if not normalized:
        return False

    if len(normalized) == 10:
        return _validate_isbn10(normalized)
    elif len(normalized) == 13:
        return _validate_isbn13(normalized)

    return False


def _validate_isbn10(isbn: str) -> bool:
    """Valide un ISBN-10."""
    if len(isbn) != 10:
        return False

    total = 0
    for i in range(9):
        if not isbn[i].isdigit():
            return False
        total += int(isbn[i]) * (10 - i)

    # Dernière position peut être X (=10)
    checksum = isbn[9]
    if checksum == "X":
        total += 10
    elif checksum.isdigit():
        total += int(checksum)
    else:
        return False

    return total % 11 == 0


def _validate_isbn13(isbn: str) -> bool:
    """Valide un ISBN-13."""
    if len(isbn) != 13:
        return False

    total = 0
    for i in range(12):
        if not isbn[i].isdigit():
            return False
        multiplier = 1 if i % 2 == 0 else 3
        total += int(isbn[i]) * multiplier

    checksum = (10 - (total % 10)) % 10
    return checksum == int(isbn[12]) if isbn[12].isdigit() else False
