"""Dialog d'alerte pour les prêts en retard."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QPushButton, QVBoxLayout, QWidget

from ..services.translation_service import translate


class OverdueAlertDialog(QDialog):
    """
    Dialog modal affichant une alerte pour les prêts en retard.

    Signals:
        viewOverduesRequested: Émis quand l'utilisateur veut voir la liste des retards
    """

    viewOverduesRequested = Signal()

    def __init__(self, overdue_count: int, parent: QWidget | None = None):
        """
        Initialise le dialog d'alerte.

        Args:
            overdue_count: Nombre de prêts en retard
            parent: Widget parent
        """
        super().__init__(parent)

        self.overdue_count = overdue_count

        self.setWindowTitle(translate("overdue_alert.title"))
        self.setModal(True)
        self.setMinimumWidth(400)

        self._setup_ui()

    def _setup_ui(self):
        """Configure l'interface du dialog."""
        layout = QVBoxLayout(self)

        # Message principal
        if self.overdue_count == 1:
            message_text = translate("overdue_alert.message_singular")
        else:
            message_text = translate("overdue_alert.message_plural").format(
                count=self.overdue_count
            )

        message_label = QLabel(message_text)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(message_label)

        # Style alerte si beaucoup de retards
        if self.overdue_count > 5:
            message_label.setStyleSheet(
                "font-size: 14px; padding: 10px; color: red; font-weight: bold;"
            )

        # Boutons
        button_box = QDialogButtonBox()

        # Bouton "Voir les retards"
        view_button = QPushButton(translate("overdue_alert.view_button"))
        view_button.clicked.connect(self._on_view_clicked)
        button_box.addButton(view_button, QDialogButtonBox.ActionRole)

        # Bouton "Fermer"
        close_button = button_box.addButton(QDialogButtonBox.Close)
        close_button.setText(translate("overdue_alert.close_button"))
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

    def _on_view_clicked(self):
        """Gère le clic sur 'Voir les retards'."""
        self.viewOverduesRequested.emit()
        self.accept()
