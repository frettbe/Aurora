"""
Dialogue unifié pour la création de prêts.

Ce module remplace checkout_dialog.py et NewLoanDialog pour offrir
une interface unifiée de création de prêts, qu'elle soit initiée
depuis un livre, un membre, ou via le menu général.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select

from ..persistence.database import get_session
from ..persistence.models_sa import Book, Member
from ..services.loan_service import LoanError, create_loan
from ..services.translation_service import translate


class LoanDialog(QDialog):
    """
    Dialogue unifié pour créer un nouveau prêt.

    Paramètres optionnels permettent de pré-sélectionner le livre ou le membre
    selon le contexte d'appel (clic droit sur livre, sur membre, ou menu général).
    """

    def __init__(
        self,
        parent: QWidget,
        book: Book | None = None,
        member: Member | None = None,
    ):
        """
        Initialise le dialogue de prêt.

        Args:
            parent: Le widget parent.
            book: Livre pré-sélectionné (optionnel, ex: clic droit sur livre).
            member: Membre pré-sélectionné (optionnel, ex: clic droit sur membre).
        """
        super().__init__(parent)
        self.setWindowTitle(translate("loan_dialog.title"))

        self.setMinimumWidth(400)
        self.setMaximumWidth(600)
        self.resize(500, 200)  # Largeur: 500px, Hauteur: 200px

        self._preselected_book = book
        self._preselected_member = member

        # Widgets
        self.book_combo = QComboBox()
        self.member_combo = QComboBox()

        # Layout
        form_layout = QFormLayout()
        form_layout.addRow(translate("loan_dialog.label_book"), self.book_combo)
        form_layout.addRow(translate("loan_dialog.label_member"), self.member_combo)

        # Boutons standard OK/Cancel
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self._on_accept)
        self.buttons.rejected.connect(self.reject)

        main_layout = QVBoxLayout(self)
        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.buttons)

        # Chargement des données
        self._load_books()
        self._load_members()

    def _load_books(self):
        """Charge la liste des livres disponibles (copies_available > 0)."""
        self.book_combo.clear()

        with get_session() as session:
            books = session.scalars(
                select(Book).filter(Book.copies_available > 0).order_by(Book.title)
            ).all()

            for book in books:
                label = f"{book.title} ({book.author or 'N/A'})"
                self.book_combo.addItem(label, book.id)

            # 🔥 Pré-sélection si un livre est fourni
            if self._preselected_book:
                idx = self.book_combo.findData(self._preselected_book.id)
                if idx >= 0:
                    self.book_combo.setCurrentIndex(idx)
                    # Désactiver le combo si pré-sélectionné (contexte = clic droit)
                    self.book_combo.setEnabled(False)

    def _load_members(self):
        """Charge la liste des membres actifs."""
        self.member_combo.clear()

        with get_session() as session:
            members = session.scalars(
                select(Member)
                .filter_by(is_active=True)
                .order_by(Member.member_no, Member.last_name, Member.first_name)
            ).all()

            for member in members:
                label = f"({member.member_no}) - {member.last_name}, {member.first_name}"
                self.member_combo.addItem(label, member.id)

            # 🔥 Pré-sélection si un membre est fourni
            if self._preselected_member:
                idx = self.member_combo.findData(self._preselected_member.id)
                if idx >= 0:
                    self.member_combo.setCurrentIndex(idx)
                    # Désactiver le combo si pré-sélectionné
                    self.member_combo.setEnabled(False)

    @Slot()
    def _on_accept(self):
        """Valide et crée le prêt via loan_service."""
        book_id = self.book_combo.currentData()
        member_id = self.member_combo.currentData()

        # Validations basiques
        if book_id is None:
            QMessageBox.warning(
                self,
                translate("errors.missing_data"),
                translate("errors.book_not_selected"),
            )
            return

        if member_id is None:
            QMessageBox.warning(
                self,
                translate("errors.missing_data"),
                translate("errors.member_not_selected"),
            )
            return

        # 🔥 Appel au service centralisé
        try:
            create_loan(
                book_id=book_id,
                member_id=member_id,
                loan_date=date.today(),
            )

            # 🎯 Si livre pré-sélectionné, mettre à jour l'objet local
            # (pour que la vue rafraîchisse sans recharger)
            if self._preselected_book:
                self._preselected_book.copies_available -= 1

            QMessageBox.information(
                self,
                translate("messages.success"),
                translate("messages.loan_created_successfully"),
            )
            self.accept()

        except LoanError as e:
            # Erreurs métier (disponibilité, niveau insuffisant, membre inactif, etc.)
            QMessageBox.warning(
                self,
                translate("errors.action_impossible"),
                str(e),
            )

        except Exception as e:
            # Erreurs inattendues
            QMessageBox.critical(
                self,
                translate("errors.unexpected_error"),
                translate("errors.unexpected_error_message").format(error=str(e)),
            )
