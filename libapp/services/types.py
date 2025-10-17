"""
Définitions des types de données personnalisés et des DTOs (Data Transfer Objects).

Ce module centralise les types complexes ou les alias de types utilisés à travers
la couche de service pour améliorer la lisibilité et la robustesse du code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ImportPolicy = Literal["merge", "skip", "replace"]


@dataclass(slots=True)
class BookRow:
    """Ligne normalisée issue du parsing XLSX/CSV."""

    titre: str
    sous_titre: str | None = None
    auteurs: list[str] | None = None
    isbn: str | None = None
    editeur: str | None = None
    date_publication: int | None = None  # année castée en int
    collection: str | None = None
    tome: int | None = None
    code_interne: str | None = None
    mots_cles: list[str] | None = None


@dataclass(slots=True)
class BookDTO:
    """DTO indépendant du modèle DB pour l’UI/échanges."""

    id: int | None
    isbn: str
    title: str
    author: str
    publisher: str | None = None
    year: int | None = None
    category: str = "apprenti"
    copies_total: int = 1
    copies_available: int = 1


@dataclass(slots=True)
class ImportErrorItem:
    """Message de validation/erreur remonté au rapport."""

    row_index: int
    field: str | None  # peut être None pour erreurs globales
    message: str
    severity: Literal["warning", "error"] = "warning"


@dataclass(slots=True)
class ImportBatch:
    """Résultat du parsing: lignes + erreurs de mapping/lecture."""

    rows: list[BookRow]
    errors: list[ImportErrorItem]


@dataclass(slots=True)
class ImportResult:
    """Statistiques d’upsert + erreurs SQL/contraintes."""

    inserted: int
    updated: int
    skipped: int
    errors: list[ImportErrorItem]
