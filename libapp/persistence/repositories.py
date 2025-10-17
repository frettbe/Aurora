"""
Implémentation du "Repository Pattern" pour l'accès aux données.

Ce module fournit des classes (Repositories) qui encapsulent la logique de
requêtage pour chaque modèle de données principal. L'objectif est de
découpler la logique métier de l'accès direct aux données (SQLAlchemy),
rendant le code plus propre, plus facile à tester et à maintenir.

Chaque Repository est responsable des opérations CRUD pour son modèle.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models_sa import Book, Loan, LoanStatus, Member


class BookRepository:
    """Gestionnaire d'accès aux objets Book dans la base de données."""

    def __init__(self, session: Session):
        """Initialise le repository avec une session SQLAlchemy."""
        self.session = session

    def list(self) -> list[Book]:
        """Retourne la liste de tous les livres, triés par titre."""
        return self.session.query(Book).order_by(Book.title).all()

    def get(self, book_id: int) -> Book | None:
        """Récupère un livre par son identifiant unique."""
        return self.session.get(Book, book_id)

    def add(self, book: Book) -> Book:
        """Ajoute un nouveau livre à la session."""
        self.session.add(book)
        return book

    def update(self, book: Book) -> Book:
        """
        Marque un livre existant comme modifié dans la session.
        NOTE: SQLAlchemy gère l'état de l'objet. L'appel à `add`
        fonctionne aussi pour les mises à jour si l'objet est déjà
        suivi par la session.
        """
        self.session.add(book)
        return book

    def delete(self, book: Book) -> None:
        """Supprime un livre de la session."""
        self.session.delete(book)


class MemberRepository:
    """Gestionnaire d'accès aux objets Member dans la base de données."""

    def __init__(self, session: Session):
        """Initialise le repository avec une session SQLAlchemy."""
        self.session = session

    def list(self) -> list[Member]:
        """Retourne la liste de tous les membres, triés par nom."""
        return self.session.query(Member).order_by(Member.last_name, Member.first_name).all()

    def get(self, member_id: int) -> Member | None:
        """Récupère un membre par son identifiant unique."""
        return self.session.get(Member, member_id)

    def add(self, member: Member) -> Member:
        """Ajoute un nouveau membre à la session."""
        self.session.add(member)
        return member

    def update(self, member: Member) -> Member:
        """Marque un membre existant comme modifié dans la session."""
        self.session.add(member)
        return member

    def delete(self, member: Member) -> None:
        """Supprime un membre de la session."""
        self.session.delete(member)


class LoanRepository:
    """Gestionnaire d'accès aux objets Loan dans la base de données."""

    def __init__(self, session: Session):
        """Initialise le repository avec une session SQLAlchemy."""
        self.session = session

    def get(self, loan_id: int) -> Loan | None:
        """Récupère un prêt par son identifiant unique."""
        return self.session.get(Loan, loan_id)

    def add(self, loan: Loan) -> Loan:
        """Ajoute un nouveau prêt à la session."""
        self.session.add(loan)
        return loan

    def update(self, loan: Loan) -> Loan:
        """Marque un prêt existant comme modifié dans la session."""
        self.session.add(loan)
        return loan

    def list_open_by_member(self, member_id: int) -> list[Loan]:
        """Retourne la liste des prêts en cours pour un membre donné."""
        return (
            self.session.execute(
                select(Loan).where(Loan.member_id == member_id, Loan.status == LoanStatus.open)
            )
            .scalars()
            .all()
        )

    def list_open_by_book(self, book_id: int) -> list[Loan]:
        """Retourne la liste des prêts en cours pour un livre donné."""
