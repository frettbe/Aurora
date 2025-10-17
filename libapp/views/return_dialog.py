"""
Boîte de dialogue pour retourner un prêt.

Ce module contient uniquement ReturnLoanDialog.
NewLoanDialog a été remplacé par LoanDialog (dans loan_dialog.py).
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
from ..persistence.models_sa import Loan, LoanStatus
from ..services.translation_service import translate


class ReturnLoanDialog(QDialog):
    """
    Dialogue pour sélectionner et retourner un prêt ouvert.

    Affiche la liste des prêts en cours avec le livre et le membre associés,
    et permet de marquer le prêt comme retourné.
    """

    def __init__(
        self, parent: QWidget | None = None, preselected_loan_id: int | None = None
    ):  # 🔥 Ajoute le paramètre
        """
        Initialise le dialogue de retour de prêt.

        Args:
            parent: Widget parent.
            preselected_loan_id: ID du prêt à pré-sélectionner (optionnel).
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

        self._populate_combo()  # Charge les prêts

    def _load_open_loans(self):
        """Charge la liste des prêts ouverts dans le combo."""
        self.loan_combo.clear()

        with get_session() as session:
            # Charger les prêts ouverts avec le livre et le membre (jointure)
            open_loans = session.scalars(
                select(Loan)
                .filter_by(status=LoanStatus.open)
                .options(joinedload(Loan.book), joinedload(Loan.member))
                .order_by(Loan.loan_date.desc())
            ).all()

            for loan in open_loans:
                book_title = loan.book.title if loan.book else "N/A"
                member_name = (
                    f"{loan.member.last_name} {loan.member.first_name}" if loan.member else "N/A"
                )
                label = f"{book_title} → {member_name} ({loan.loan_date})"
                self.loan_combo.addItem(label, loan.id)

        if self.loan_combo.count() == 0:
            QMessageBox.information(
                self,
                translate("loan_dialogs.no_open_loans_title"),
                translate("loan_dialogs.no_open_loans_message"),
            )
            self.reject()

    def get_selected_loan_id(self) -> int | None:
        """
        Retourne l'ID du prêt sélectionné.

        Returns:
            L'ID du prêt ou None si aucune sélection.
        """
        return self.loan_combo.currentData()
