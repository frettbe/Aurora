"""
Fenêtre de dialogue pour la création et l'édition d'une fiche Membre.

Ce module contient la classe `MemberEditor`, qui est un formulaire complet
permettant de renseigner toutes les informations d'un membre. Il inclut
également une logique de validation pour garantir l'intégrité des données.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import Integer, func, select

from ..persistence.database import get_session
from ..persistence.models_sa import Member
from ..services.translation_service import translate


class MemberEditor(QDialog):
    """Dialogue modal pour créer ou modifier les informations d'un membre."""

    def __init__(self, parent: QWidget | None = None, member: Member | None = None):
        super().__init__(parent)
        self.setWindowTitle(
            translate("member_editor.edit_title")
            if member
            else translate("member_editor.new_title")
        )
        self.setMinimumWidth(400)
        self._member = member
        self.result_data: dict[str, Any] = {}

        # --- Construction de l'UI (méthodes restaurées) ---
        self._setup_ui()
        self._connect_signals()
        if self._member:
            self._populate_form()

    def _setup_ui(self):
        """Construit l'interface utilisateur du dialogue."""
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.member_no_input = QLineEdit()
        self.first_name_input = QLineEdit()
        self.last_name_input = QLineEdit()
        self.email_input = QLineEdit()
        self.phone_input = QLineEdit()
        # self.member_status_input = QComboBox()
        # self.member_status_input.addItem(translate("member.status_apprenti"), "apprenti")
        # self.member_status_input.addItem(translate("member.status_compagnon"), "compagnon")
        # self.member_status_input.addItem(translate("member.status_maitre"), "maitre")
        self.active_input = QCheckBox(translate("member.is_active"))

        form_layout.addRow(translate("member.member_no"), self.member_no_input)
        form_layout.addRow(translate("member.first_name"), self.first_name_input)
        form_layout.addRow(translate("member.last_name"), self.last_name_input)
        form_layout.addRow(translate("member.email"), self.email_input)
        form_layout.addRow(translate("member.phone"), self.phone_input)
        form_layout.addRow(translate("member.is_active_label"), self.active_input)
        main_layout.addLayout(form_layout)

        # 🔥 Créer les boutons personnalisés
        self.button_box = QDialogButtonBox()
        self.button_box.addButton(translate("buttons.save"), QDialogButtonBox.ButtonRole.AcceptRole)
        self.button_box.addButton(
            translate("buttons.cancel"), QDialogButtonBox.ButtonRole.RejectRole
        )
        main_layout.addWidget(self.button_box)

    def _connect_signals(self):
        """Connecte les signaux des widgets."""
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def _populate_form(self):
        """Pré-remplit le formulaire avec les données d'un membre existant."""
        if not self._member:
            return
        self.member_no_input.setText(self._member.member_no)
        self.first_name_input.setText(self._member.first_name)
        self.last_name_input.setText(self._member.last_name)
        self.email_input.setText(self._member.email)
        self.phone_input.setText(self._member.phone or "")
        self.active_input.setChecked(self._member.is_active)

    def accept(self):
        """Valide et enregistre les modifications."""
        # Validation des champs obligatoires
        if not self.last_name_input.text().strip():
            QMessageBox.warning(
                self,
                translate("member_editor.error_title"),
                translate("member_editor.error_last_name_required"),
            )
            return

        if not self.first_name_input.text().strip():
            QMessageBox.warning(
                self,
                translate("member_editor.error_title"),
                translate("member_editor.error_first_name_required"),
            )
            return

        try:
            # Génération auto du numéro de membre si vide
            member_no = self.member_no_input.text().strip()

            if not member_no:
                # Générer un numéro automatique
                with get_session() as session:
                    # Récupérer le numéro max actuel
                    result = session.execute(
                        select(
                            func.max(func.cast(func.substr(Member.member_no, 2), Integer))
                        ).where(Member.member_no.like("M%"))
                    ).scalar()

                    next_num = (result or 0) + 1
                    member_no = f"M{next_num:04d}"  # Format M0001, M0002, etc.

            # Sauvegarder le membre
            with get_session() as session:
                if self._member:
                    # Mode édition
                    member = session.merge(self._member)
                else:
                    # Mode création
                    member = Member()
                    session.add(member)

                # Mettre à jour les champs
                member.member_no = member_no
                member.last_name = self.last_name_input.text().strip()
                member.first_name = self.first_name_input.text().strip()
                member.email = self.email_input.text().strip() or None
                member.phone = self.phone_input.text().strip() or None
                member.is_active = self.active_input.isChecked()

                session.commit()
                session.expunge(member)  # 🔧 FIX refresh !

            super().accept()

        except Exception as e:
            print("debug:", str(e))
            QMessageBox.critical(
                self,
                translate("member_editor.error_title"),
                translate("member_editor.error_save", error=str(e)),
            )
