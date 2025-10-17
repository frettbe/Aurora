"""
Implémentation du pattern "Unit of Work" pour la gestion des transactions.

Ce module fournit une classe `UnitOfWork` qui agit comme un context manager
pour encapsuler une transaction de base de données complète. Elle garantit
que toutes les opérations effectuées dans un bloc `with` sont atomiques.
"""

from __future__ import annotations

from contextlib import AbstractContextManager

from .database import get_session
from .repositories import BookRepository, LoanRepository, MemberRepository


class UnitOfWork(AbstractContextManager):
    """
    Gestionnaire de transaction et d'unité de travail.

    Cette classe est un context manager qui automatise l'ouverture,
    la gestion (commit/rollback) et la fermeture des sessions SQLAlchemy.
    Elle regroupe également les instances des repositories pour un accès
    centralisé aux données au sein d'une même transaction.

    Exemple d'utilisation :
        with UnitOfWork() as uow:
            book = uow.books.get(1)
            book.title = "Nouveau Titre"
            uow.commit() # Optionnel, car le commit est automatique

    Attributs après entrée dans le contexte :
        session (Session): La session SQLAlchemy active pour la transaction.
        books (BookRepository): Le repository pour les livres.
        members (MemberRepository): Le repository pour les membres.
        loans (LoanRepository): Le repository pour les prêts.
    """

    def __init__(self, session_factory=get_session):
        """Initialise l'unité de travail avec une factory de session."""
        self._session_factory = session_factory
        self.session = None
        self.books: BookRepository | None = None
        self.members: MemberRepository | None = None
        self.loans: LoanRepository | None = None

    def __enter__(self):
        """
        Démarre une nouvelle transaction.

        Ouvre une session et initialise tous les repositories avec celle-ci.
        """
        self.session = self._session_factory()
        self.books = BookRepository(self.session)
        self.members = MemberRepository(self.session)
        self.loans = LoanRepository(self.session)
        return self

    def __exit__(self, exc_type, exc_val, traceback):
        """
        Termine la transaction.

        Effectue un commit si aucune exception n'a été levée dans le bloc `with`.
        Sinon, effectue un rollback. La session est toujours fermée.
        """
        try:
            if exc_type is None:
                self.session.commit()
            else:
                self.session.rollback()
        finally:
            self.session.close()

    def commit(self):
        """Force un commit des changements en cours de transaction."""
        self.session.commit()

    def rollback(self):
        """Force un rollback des changements en cours de transaction."""
        self.session.rollback()
