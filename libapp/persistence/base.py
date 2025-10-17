"""
Définition de la base déclarative unique pour les modèles ORM SQLAlchemy.

Cette classe `Base` sert de fondation commune pour tous les modèles
de l'application (Book, Member, etc.), leur permettant d'être découverts
et gérés par le metadata de SQLAlchemy.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base déclarative unique partagée par tous les modèles."""

    pass
