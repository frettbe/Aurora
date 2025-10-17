"""
Module de gestion de la connexion et de la création de la base de données.

Ce module configure le moteur SQLAlchemy pour une base SQLite locale,
définit la session, et fournit des fonctions pour assurer l'existence
des tables et peupler la base avec des données de démonstration.

Fonctions principales :
- get_session(): Retourne une session SQLAlchemy pour les opérations.
- ensure_tables(): Crée toutes les tables à partir des modèles si elles n'existent pas.
"""

from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from libapp.utils.paths import db_path

from .base import Base

# --- Configuration du moteur et de la session SQLAlchemy ---
# La base de données est stockée dans le dossier de données de l'application.
DATABASE_URL = f"sqlite:///{db_path().as_posix()}"
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_session():
    """
    Fournit une nouvelle session SQLAlchemy.

    Cette factory est le point d'entrée pour toutes les interactions
    avec la base de données.

    Returns:
        Session: Une nouvelle instance de session SQLAlchemy.
    """
    return SessionLocal()


def ensure_tables():
    """
    Crée toutes les tables de la base de données si elles n'existent pas.

    Cette fonction importe dynamiquement les modèles (ce qui les enregistre
    auprès du metadata de SQLAlchemy) puis appelle `create_all`. C'est la
    méthode non destructive pour s'assurer que le schéma est à jour.
    """
    # 1. Enregistrer les modèles dans le metadata (effet de bord de l'import)
    from . import models_sa  # noqa: F401

    # 2. Créer les tables manquantes
    Base.metadata.create_all(bind=engine)


def _init_db():
    """
    Initialise la base de données avec des données de démo si elle est vide.

    Cette fonction est destinée à être appelée manuellement pour le développement.
    Elle assure d'abord que les tables existent, puis vérifie si elles
    contiennent des données avant d'en insérer.
    """
    # S'assurer que le schéma est prêt
    ensure_tables()

    # Importer les modèles nécessaires pour l'insertion
    from .models_sa import Book, BookCategory, Member, MemberStatus

    with get_session() as s:
        # Vérifier si la table des livres est vide
        book_count = s.execute(text("SELECT COUNT(1) FROM books")).scalar_one()
        if book_count == 0:
            print("Base de données vide, insertion des données de démonstration...")
            s.add_all(
                [
                    Book(
                        isbn="978000000001",
                        title="Le Petit Prince",
                        author="Saint-Exupéry",
                        publisher="Gallimard",
                        year=1943,
                        category=BookCategory.apprenti,
                        copies_total=3,
                        copies_available=3,
                    ),
                    Book(
                        isbn="978000000002",
                        title="Candide",
                        author="Voltaire",
                        publisher="",
                        year=1759,
                        category=BookCategory.compagnon,
                        copies_total=2,
                        copies_available=2,
                    ),
                ]
            )

        # Vérifier si la table des membres est vide
        member_count = s.execute(text("SELECT COUNT(1) FROM members")).scalar_one()
        if member_count == 0:
            s.add_all(
                [
                    Member(
                        member_no="M001",
                        first_name="Alice",
                        last_name="Dupont",
                        email="alice@ex.com",
                    ),
                    Member(
                        member_no="M002",
                        first_name="Bob",
                        last_name="Martin",
                        email="bob@ex.com",
                        status=MemberStatus.compagnon,
                    ),
                ]
            )

        s.commit()


if __name__ == "__main__":
    import sys

    if "--init" in sys.argv:
        print(f"Initialisation de la base de données à l'emplacement : {DATABASE_URL}")
        _init_db()
        print("Initialisation terminée.")
    else:
        print("Usage: python -m libapp.persistence.database --init")
