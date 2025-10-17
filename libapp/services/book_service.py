"""
Service de gestion de la logique métier des Livres.

Ce module fournit les opérations de haut niveau (CRUD) pour les livres,
en encapsulant l'accès à la base de données via le pattern Unit of Work.
Il utilise un DTO (Data Transfer Object) pour découpler la couche de
présentation de la couche de persistance.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from ..persistence.models_sa import Book, BookCategory
from ..persistence.unit_of_work import UnitOfWork

logger = logging.getLogger("library.services.book")


@dataclass
class BookDTO:
    """
    Data Transfer Object pour un Livre.

    Représente les données d'un livre telles qu'elles transitent entre
    l'interface utilisateur et la couche de service. Ne contient que des
    types de données simples.
    """

    id: int | None
    isbn: str
    title: str
    author: str
    publisher: str | None = None
    year: int | None = None
    category: str = "apprenti"
    copies_total: int = 1
    copies_available: int = 1


class BookService:
    """Service gérant la logique métier des livres (CRUD)."""

    def __init__(self, uow_factory=lambda: UnitOfWork()):
        """Initialise le service avec une factory d'unités de travail."""
        self.uow_factory = uow_factory

    def list(self) -> list[Book]:
        """Retourne la liste de tous les livres présents en base."""
        with self.uow_factory() as uow:
            return uow.books.list()

    def create(self, dto: BookDTO) -> Book:
        """
        Crée un nouveau livre à partir d'un DTO.

        Args:
            dto (BookDTO): Les données du livre à créer.

        Returns:
            Book: L'objet Book persisté.
        """
        with self.uow_factory() as uow:
            b = Book(
                isbn=dto.isbn.strip(),
                title=dto.title.strip(),
                authors_text=dto.author.strip(),  # Note: on mappe 'author' du DTO à 'authors_text'
                publisher=(dto.publisher or "").strip(),
                year=str(dto.year) if dto.year is not None else None,
                category=BookCategory(dto.category),
                copies_total=int(dto.copies_total),
                copies_available=int(dto.copies_available),
            )
            if b.copies_available > b.copies_total:
                raise ValueError("Le nombre d'exemplaires disponibles ne peut excéder le total.")

            uow.books.add(b)
            uow.commit()
            logger.info("Création livre: %s - %s", b.isbn, b.title)
            return b

    def update(self, book_id: int, dto: BookDTO) -> Book:
        """
        Met à jour un livre existant à partir d'un DTO.

        Args:
            book_id (int): L'ID du livre à mettre à jour.
            dto (BookDTO): Les nouvelles données pour le livre.

        Returns:
            Book: L'objet Book mis à jour et persisté.

        Raises:
            ValueError: Si le livre n'est pas trouvé.
        """
        with self.uow_factory() as uow:
            b = uow.books.get(book_id)
            if not b:
                raise ValueError("Livre introuvable")

            b.isbn = dto.isbn.strip()
            b.title = dto.title.strip()
            b.authors_text = dto.author.strip()
            b.publisher = (dto.publisher or "").strip()
            b.year = str(dto.year) if dto.year is not None else None
            b.category = BookCategory(dto.category)
            b.copies_total = int(dto.copies_total)
            b.copies_available = int(dto.copies_available)

            if b.copies_available > b.copies_total:
                raise ValueError("Le nombre d'exemplaires disponibles ne peut excéder le total.")

            uow.commit()
            logger.info("MAJ livre id=%s: %s - %s", book_id, b.isbn, b.title)
            return b

    def delete(self, book_id: int) -> None:
        """Supprime un livre par son identifiant."""
        with self.uow_factory() as uow:
            b = uow.books.get(book_id)
            if not b:
                return
            uow.books.delete(b)
            uow.commit()
            logger.info("Suppression livre id=%s", book_id)
