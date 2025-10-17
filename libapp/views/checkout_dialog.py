"""
Boîte de dialogue pour la création d'un nouveau prêt de livre.

Ce module définit `CheckoutDialog`, une fenêtre modale qui permet à
l'utilisateur de sélectionner un membre et une date de retour pour
finaliser l'emprunt d'un livre.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select

from ..persistence.database import get_session
from ..persistence.models_sa import Book, Member
from ..services.loan_policy import get_policy_for_status  # 🔥 NOUVEAU
from ..services.preferences import load_preferences  # 🔥 NOUVEAU
from ..services.translation_service import translate


class CheckoutDialog(QDialog):
    """
    Dialogue d'emprunt qui associe un livre à un membre pour une durée donnée.

    Cette fenêtre charge la liste des membres actifs, propose une date de
    retour par défaut, et à la validation, crée un enregistrement `Loan`
    en base de données tout en décrémentant le nombre d'exemplaires
    disponibles pour le livre concerné.
    """

    def __init__(self, parent: QWidget, book: Book):
        """
        Initialise le dialogue d'emprunt.

        Args:
            parent: Le widget parent.
            book: L'objet `Book` qui va être emprunté.
        """
        super().__init__(parent)
        self.setWindowTitle(translate("checkout.title").format(book_title=book.title))
        self.book = book

        # 🔥 Charger les préférences UNE FOIS au début
        self.prefs = load_preferences()

        # --- Création des widgets et du layout ---
        layout = QVBoxLayout(self)

        # Sélection du membre
        member_layout = QHBoxLayout()
        member_layout.addWidget(QLabel(translate("checkout.label_member")))
        self.member_combo = QComboBox()
        member_layout.addWidget(self.member_combo)
        layout.addLayout(member_layout)

        # Sélection de la date de retour
        due_date_layout = QHBoxLayout()
        due_date_layout.addWidget(QLabel(translate("checkout.label_due_date")))
        self.due_date_edit = QDateEdit()
        self.due_date_edit.setCalendarPopup(True)
        # 🔥 Date par défaut : sera calculée après le chargement des membres
        due_date_layout.addWidget(self.due_date_edit)
        layout.addLayout(due_date_layout)

        # Boutons de validation
        buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton(translate("buttons.validate_loan"))
        self.cancel_button = QPushButton(translate("buttons.cancel"))
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)

        # --- Connexion des signaux ---
        self.ok_button.clicked.connect(self.on_accept)
        self.cancel_button.clicked.connect(self.reject)
        # 🔥 NOUVEAU : Mettre à jour la date quand le membre change
        self.member_combo.currentIndexChanged.connect(self._on_member_changed)

        # --- Initialisation des données ---
        self._load_members()

    @Slot()
    def _load_members(self):
        """
        Charge la liste des membres actifs depuis la base de données
        et les ajoute à la liste déroulante (ComboBox).
        """
        self.member_combo.clear()
        with get_session() as session:
            # On ne charge que les membres actifs, triés par nom
            members = session.scalars(
                select(Member)
                .filter_by(is_active=True)
                .order_by(Member.last_name, Member.first_name)
            ).all()
            for member in members:
                # Le texte affiché est lisible, la donnée stockée est (member.id, member.status.value)
                label = f"{member.last_name} {member.first_name} ({member.member_no})"
                # 🔥 On stocke un tuple (id, status) pour calculer la durée
                self.member_combo.addItem(label, (member.id, member.status.value))

        # 🔥 Initialiser la date pour le premier membre
        if self.member_combo.count() > 0:
            self._on_member_changed()

    @Slot()
    def _on_member_changed(self):
        """
        Met à jour la date de retour par défaut selon le statut du membre sélectionné.
        """
        data = self.member_combo.currentData()
        if data is None:
            # Pas de membre sélectionné : utiliser la durée apprenti par défaut
            default_days = self.prefs.loan_duration_apprenti
        else:
            member_id, member_status = data
            # Calculer la durée selon le statut
            policy = get_policy_for_status(member_status, self.prefs)
            default_days = policy.loan_days

        # Mettre à jour la date dans le QDateEdit
        default_due_date = QDate.currentDate().addDays(default_days)
        self.due_date_edit.setDate(default_due_date)

    @Slot()
    def on_accept(self):
        """
        Valide les sélections et crée le prêt via loan_service.

        Gère les erreurs spécifiques et les affiche de manière appropriée.
        """
        data = self.member_combo.currentData()

        if data is None:
            QMessageBox.warning(
                self,
                translate("errors.missing_data"),
                translate("errors.member_not_selected"),
            )
            return

        # 🔥 Extraire member_id du tuple
        member_id, _ = data

        # 🎯 VÉRIFICATION PRÉ-EMPTIVE : Disponibilité du livre
        # (pour donner un feedback immédiat sans appeler le service)
        if self.book.copies_available <= 0:
            QMessageBox.warning(
                self,
                translate("errors.action_impossible"),
                translate("errors.no_copies_available"),
            )
            return

        # --- Appel au service centralisé ---
        try:
            from ..services.loan_service import LoanError, create_loan

            # 🔥 Le service gère TOUT :
            # - Vérification de disponibilité (avec verrouillage optimiste)
            # - Calcul de la durée selon le statut du membre
            # - Vérification de la politique de niveau (si activée)
            # - Création du prêt
            # - Mise à jour de l'inventaire
            # - Audit
            create_loan(book_id=self.book.id, member_id=member_id, loan_date=date.today())

            # 🎯 Mettre à jour l'objet book LOCAL (pour que la vue se rafraîchisse)
            # IMPORTANT : Sans ça, book_list ne verra pas le changement !
            self.book.copies_available -= 1

            QMessageBox.information(
                self,
                translate("messages.success"),
                translate("messages.loan_success").format(book_title=self.book.title),
            )
            self.accept()

        except LoanError as e:
            # Erreurs métier (livre indisponible, membre inactif, niveau insuffisant, etc.)
            QMessageBox.warning(
                self,
                translate("errors.action_impossible"),
                str(e),
            )

        except Exception as e:
            # Erreurs inattendues (base de données, etc.)
            QMessageBox.critical(
                self,
                translate("errors.unexpected_error"),
                translate("errors.unexpected_error_message").format(error=str(e)),
            )
