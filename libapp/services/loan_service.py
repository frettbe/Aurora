"""Service de gestion des prêts (création, retour).

Ce module contient la logique métier pour toutes les opérations
liées aux prêts, en s'assurant que les règles (disponibilité,
statut du membre) sont respectées.
"""

from __future__ import annotations

from datetime import date, timedelta

from ..persistence.database import get_session
from ..persistence.models_sa import Book, Loan, LoanStatus, Member
from ..services.audit_service import audit_loan_created, audit_loan_returned


class LoanError(Exception):
    """Exception levée pour les erreurs liées à la logique des prêts."""


def is_overdue(due: date | None, ret: date | None) -> bool:
    """Vérifie si un prêt est en retard.

    Args:
        due: Date d'échéance du prêt.
        ret: Date de retour du prêt.

    Returns:
        True si le prêt est en retard, False sinon.
    """
    if ret:  # S'il est rendu, il n'est plus en retard
        return False
    if not due:  # S'il n'a pas de date d'échéance, il ne peut être en retard
        return False
    return date.today() > due


def create_loan(book_id: int, member_id: int, loan_date: date | None = None) -> Loan:
    """Crée un nouveau prêt en respectant les règles métier.

    Args:
        book_id: ID du livre à emprunter.
        member_id: ID du membre qui emprunte.
        loan_date: La date du prêt (aujourd'hui par défaut).

    Returns:
        L'objet Loan nouvellement créé.

    Raises:
        LoanError: Si les règles de prêt ne sont pas respectées.
    """
    with get_session() as session:
        # Charger les objets dans CETTE session
        book = session.get(Book, book_id)
        member = session.get(Member, member_id)

        if not book:
            raise LoanError("Livre introuvable.")
        if not member:
            raise LoanError("Membre introuvable.")

        # Règle 1: Le livre doit être disponible
        if book.copies_available <= 0:
            raise LoanError("Ce livre n'est pas disponible pour le prêt.")

        # Règle 2: Le membre doit être actif
        if not member.is_active:
            raise LoanError("Ce membre n'est pas actif et ne peut pas emprunter.")

        # Charger les préférences pour la durée de prêt
        from ..services.preferences import load_preferences

        prefs = load_preferences()

        # Calculer la date d'échéance avec la durée par défaut
        loan_date = loan_date or date.today()
        due_date = loan_date + timedelta(days=prefs.default_loan_days)

        # Créer l'objet et mettre à jour l'inventaire
        new_loan = Loan(
            book_id=book.id,
            member_id=member.id,
            loan_date=loan_date,
            due_date=due_date,
            status=LoanStatus.open,
        )

        book.copies_available -= 1

        session.add(new_loan)
        session.commit()
        session.refresh(new_loan)

        # Audit
        audit_loan_created(
            loan_id=new_loan.id,
            book_id=book.id,
            member_id=member.id,
            book_title=book.title or "(sans titre)",
            member_name=f"{member.last_name} {member.first_name}",
            user="system",
        )

        return new_loan


def return_loan(loan_id: int) -> None:
    """Marque le prêt comme retourné et incrémente copies_available si possible.

    Args:
        loan_id: ID du prêt à retourner.

    Raises:
        LoanError: Si le prêt est introuvable.
    """
    with get_session() as session:
        ln = session.get(Loan, loan_id)
        if not ln:
            raise LoanError("Prêt introuvable.")
        if ln.return_date:
            return  # déjà retourné

        # Charger les infos pour l'audit AVANT le retour
        book = session.get(Book, ln.book_id)
        member = session.get(Member, ln.member_id)
        book_title = book.title if book else "(inconnu)"
        member_name = f"{member.last_name} {member.first_name}" if member else "(inconnu)"

        # Effectuer le retour
        ln.return_date = date.today()
        ln.status = LoanStatus.returned

        if book is not None:
            book.copies_available = (book.copies_available or 0) + 1

        session.commit()

        # Audit : Logger le retour du prêt
        audit_loan_returned(
            loan_id=loan_id,
            book_id=ln.book_id,
            member_id=ln.member_id,
            book_title=book_title,
            member_name=member_name,
            user="system",
        )


def get_overdue_count() -> int:
    """Compte le nombre de prêts en retard.

    Returns:
        Le nombre de prêts ouverts dont la date d'échéance est dépassée.
    """
    from sqlalchemy import func, select

    today = date.today()
    with get_session() as session:
        count = session.scalar(
            select(func.count(Loan.id)).where(Loan.status == LoanStatus.open, Loan.due_date < today)
        )
        return int(count or 0)
