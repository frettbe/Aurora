"""
Script de migration manuelle pour la base de données SQLite.

Ce module fournit des fonctions pour faire évoluer le schéma de la base de
données sans perte de données, par exemple en ajoutant des colonnes
manquantes à des tables existantes.

Usage :
    python -m libapp.persistence.migrate --upgrade
"""

from __future__ import annotations

import sys

from sqlalchemy import text

from libapp.persistence.database import engine


def column_exists(table: str, col: str) -> bool:
    """Vérifie si une colonne existe dans une table donnée."""
    with engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        return any(r[1] == col for r in rows)


def upgrade():
    """
    Applique les migrations nécessaires au schéma de la base de données.

    Actuellement, vérifie et ajoute les colonnes `code`, `volume` et `fund`
    à la table `books` si elles sont absentes.
    """
    with engine.begin() as conn:
        if not column_exists("books", "code"):
            conn.execute(text("ALTER TABLE books ADD COLUMN code VARCHAR(50)"))

        if not column_exists("books", "volume"):
            conn.execute(text("ALTER TABLE books ADD COLUMN volume VARCHAR(50)"))

        if not column_exists("books", "fund"):
            conn.execute(text("ALTER TABLE books ADD COLUMN fund VARCHAR(100)"))

    print("Migration terminée : les colonnes nécessaires sont disponibles.")


if __name__ == "__main__":
    if "--upgrade" in sys.argv:
        upgrade()
    else:
        print("Usage: python -m libapp.persistence.migrate --upgrade")
