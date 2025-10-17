"""Boîtes de dialogue modales pour la gestion des prêts.

- NewLoanDialog: Permet de créer un nouveau prêt.
- ReturnLoanDialog: Permet de sélectionner un prêt ouvert pour le retourner.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QMessageBox,
    QWidget,
)
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from ..persistence.database import get_session
from ..persistence.models_sa import Book, Loan, LoanStatus, Member
from ..services.loan_service import LoanError, create_loan
from ..services.translation_service import translate


class NewLoanDialog(QDialog):
    """Dialogue pour la création d'un nouveau prêt."""

    def __init__(self, parent: QWidget | None = None):
        """Initialise le dialogue de création de prêt.

        Args:
            parent: Le widget parent.
        """
        super().__init__(parent)
        self.setWindowTitle(translate("loan_dialogs.new_loan_title"))

        self.book_combo = QComboBox()
        self.member_combo = QComboBox()

        form_layout = QFormLayout(self)
        form_layout.addRow(translate("loan_dialogs.label_book"), self.book_combo)
        form_layout.addRow(translate("loan_dialogs.label_member"), self.member_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form_layout.addWidget(buttons)

        self._populate_combos()

    def _populate_combos(self):
        """Remplit les listes déroulantes avec les livres disponibles et les membres actifs."""
        with get_session() as s:
            # Livres disponibles
            available_books = s.scalars(
                select(Book).where(Book.copies_available > 0).order_by(Book.title)
            ).all()

            for book in available_books:
                self.book_combo.addItem(f"{book.title} (Dispo: {book.copies_available})", book.id)

            # Membres actifs
            active_members = s.scalars(
                select(Member).where(Member.is_active).order_by(Member.last_name)
            ).all()

            for member in active_members:
                self.member_combo.addItem(f"{member.first_name} {member.last_name}", member.id)

    def accept(self):
        """Tente de créer le prêt lorsque l'utilisateur clique sur OK."""
        book_id = self.book_combo.currentData()
        member_id = self.member_combo.currentData()

        if not book_id or not member_id:
            QMessageBox.warning(
                self,
                translate("errors.error_title"),
                translate("loan_dialogs.error_select_book_member"),
            )
            return

        try:
            create_loan(book_id, member_id)
            super().accept()  # Ferme la boîte de dialogue si succès
        except LoanError as e:
            QMessageBox.critical(
                self,
                translate("errors.error_title"),
                str(e),
            )


class ReturnLoanDialog(QDialog):
    """Dialogue pour le retour d'un prêt existant."""

    def __init__(self, parent: QWidget | None = None, preselected_loan_id: int | None = None):
        """Initialise le dialogue de retour de prêt.

        Args:
            parent: Le widget parent.
            preselected_loan_id: L'ID d'un prêt à présélectionner dans la liste.
        """
        super().__init__(parent)
        self.setWindowTitle(translate("loan_dialogs.return_loan_title"))

        self.selected_loan_id: int | None = None
        self._preselected_loan_id = preselected_loan_id

        self.loan_combo = QComboBox()

        form_layout = QFormLayout(self)
        form_layout.addRow(translate("loan_dialogs.label_loan_to_return"), self.loan_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form_layout.addWidget(buttons)

        self._populate_combo()

    def _populate_combo(self):
        """Remplit la liste déroulante avec les prêts actuellement ouverts."""
        with get_session() as s:
            open_loans = s.scalars(
                select(Loan)
                .where(Loan.status == LoanStatus.open)
                .options(joinedload(Loan.book), joinedload(Loan.member))
                .order_by(Loan.due_date)
            ).all()

            if not open_loans:
                self.loan_combo.addItem(translate("loan_dialogs.no_open_loans"))
                self.loan_combo.setEnabled(False)
            else:
                for loan in open_loans:
                    book_title = loan.book.title if loan.book else "N/A"
                    member_name = (
                        f"{loan.member.first_name} {loan.member.last_name}".strip()
                        if loan.member
                        else "N/A"
                    )
                    self.loan_combo.addItem(f"'{book_title}' par {member_name}", loan.id)

                # Présélectionner un prêt si spécifié
                if self._preselected_loan_id:
                    idx = self.loan_combo.findData(self._preselected_loan_id)
                    if idx >= 0:
                        self.loan_combo.setCurrentIndex(idx)

    def accept(self):
        """Stocke l'ID du prêt sélectionné et ferme la boîte de dialogue."""
        self.selected_loan_id = self.loan_combo.currentData()

        if not self.selected_loan_id:
            QMessageBox.warning(
                self,
                translate("loan_dialogs.selection_required_title"),
                translate("loan_dialogs.selection_required_body"),
            )
            return

        super().accept()
