"""
Définition des modèles de données SQLAlchemy pour l'application Biblio.

Ce module contient les classes qui mappent les objets Python aux tables de la
base de données via l'ORM SQLAlchemy. Il définit la structure des tables,
les relations entre elles (y compris many-to-many), et les types de données
pour les livres, auteurs, membres et prêts.

Classes principales :
- Author: Représente un auteur.
- Book: Représente une fiche de livre, avec ses métadonnées.
- Member: Représente un membre de la bibliothèque.
- Loan: Représente un prêt d'un livre à un membre.

Contient également les tables d'association et les énumérations (Enum)
pour les statuts et catégories.
"""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

# Table d'association pour la relation Many-to-Many entre Livre et Auteur.
book_authors = Table(
    "book_authors",
    Base.metadata,
    Column("book_id", ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
    Column("author_id", ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True),
)


class Author(Base):
    """Modèle ORM pour un Auteur."""

    __tablename__ = "authors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    books = relationship("Book", secondary=book_authors, back_populates="authors")


# --- Énumérations pour les statuts et catégories ---


class MemberStatus(str, enum.Enum):
    """Définit les statuts possibles pour un membre."""

    apprenti = "apprenti"
    compagnon = "compagnon"
    maitre = "maitre"


class BookCategory(str, enum.Enum):
    """Définit les catégories possibles pour un livre."""

    apprenti = "apprenti"
    compagnon = "compagnon"
    maitre = "maitre"


class LoanStatus(str, enum.Enum):
    """Définit les statuts possibles pour un prêt."""

    open = "open"
    returned = "returned"


# --- Modèles principaux ---


class Book(Base):
    """
    Modèle ORM pour un Livre.

    Cette table est la 'source de vérité' pour toutes les informations
    relatives à un livre. Elle contient des alias via des 'hybrid_property'
    pour assurer la compatibilité avec l'ancien code de l'interface utilisateur.
    """

    __tablename__ = "books"

    # --- Colonnes de la base de données ---
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String)
    authors_text: Mapped[str | None] = mapped_column(String)  # Dénormalisé pour la recherche
    publisher: Mapped[str | None] = mapped_column(String)
    year: Mapped[str | None] = mapped_column(String)
    isbn: Mapped[str | None] = mapped_column(String, index=True)
    copies_total: Mapped[int] = mapped_column(Integer, default=1)
    copies_available: Mapped[int] = mapped_column(Integer, default=1)
    collection: Mapped[str | None] = mapped_column(String)
    volume: Mapped[int | None] = mapped_column(Integer)
    code_interne: Mapped[str | None] = mapped_column(String, index=True)
    mots_cles: Mapped[str | None] = mapped_column(String)
    category: Mapped[BookCategory | None] = mapped_column(Enum(BookCategory))

    # --- Relations ---
    authors = relationship("Author", secondary=book_authors, back_populates="books")

    # --- Index pour optimiser les recherches ---
    __table_args__ = (
        Index("ix_book_title", "title"),
        Index("ix_book_authors_text", "authors_text"),
        Index("ix_book_year", "year"),
    )

    # --- ALIAS pour compatibilité avec l'ancien code ---
    # Les propriétés ci-dessous permettent à l'UI et à l'ancien code d'accéder
    # aux champs avec leurs noms français (ex: b.auteur) tout en utilisant
    # des noms de colonnes en anglais dans la base de données (ex: b.authors_text).

    @hybrid_property
    def code(self):
        """Alias pour `code_interne`."""
        return self.code_interne

    @code.setter
    def code(self, v):
        self.code_interne = v

    @hybrid_property
    def author(self):
        """Alias pour `authors_text`."""
        return self.authors_text

    @author.setter
    def author(self, v):
        self.authors_text = v

    @property
    def fund(self) -> str | None:
        """Alias pour collection (compatibilité vue)."""
        return self.collection

    # ... (les autres alias peuvent être documentés de la même manière) ...


class Member(Base):
    """Modèle ORM pour un Membre de la bibliothèque."""

    __tablename__ = "members"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_no: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[MemberStatus] = mapped_column(Enum(MemberStatus), default=MemberStatus.apprenti)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    date_joined: Mapped[date | None] = mapped_column(Date)
    __table_args__ = (Index("ix_members_last_first", "last_name", "first_name"),)


class Loan(Base):
    """Modèle ORM pour un Prêt."""

    __tablename__ = "loans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False, index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), nullable=False, index=True)
    loan_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    return_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[LoanStatus] = mapped_column(
        Enum(LoanStatus), default=LoanStatus.open, nullable=False
    )

    # --- Relations ---
    book = relationship("Book")
    member = relationship("Member")

    __table_args__ = (
        Index("ix_loans_status", "status"),
        Index("ix_loans_due", "due_date"),
    )


class AuditLog(Base):
    """Table d'audit des actions utilisateur."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    action: Mapped[str] = mapped_column(
        String(50), index=True
    )  # CREATE, UPDATE, DELETE, IMPORT, EXPORT, LOAN, RETURN
    entity_type: Mapped[str] = mapped_column(String(50))  # book, member, loan
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user: Mapped[str | None] = mapped_column(
        String(100)
    )  # Nom utilisateur (si multi-user plus tard)
    details: Mapped[str | None] = mapped_column(Text)  # JSON avec détails supplémentaires
    level: Mapped[str] = mapped_column(String(10), default="INFO")  # INFO, WARNING, ERROR

    def __repr__(self):
        return f"<AuditLog {self.timestamp} {self.action} {self.entity_type}>"
