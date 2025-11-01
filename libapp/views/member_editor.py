"""
Fenêtre de dialogue pour la création et l'édition d'une fiche Membre.

Ce module contient la classe `MemberEditor`, qui est un formulaire complet
permettant de renseigner toutes les informations d'un membre. Il inclut
également une logique de validation pour garantir l'intégrité des données.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import Integer, func, select

from ..persistence.database import get_session
from ..persistence.models_sa import Member
from ..services.translation_service import translate
from ..utils.paths import user_profile_images_dir


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
        self._new_profile_path = None
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
        self.active_input = QCheckBox(translate("member.is_active"))

        self.profile_preview = QLabel()
        self.profile_preview.setFixedSize(128, 128)
        self.profile_preview.setScaledContents(True)
        self.profile_preview.setStyleSheet("border: 1px solid #ccc; border-radius: 4px;")
        self.profile_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Boutons gestion photo
        profile_btn_layout = QHBoxLayout()
        self.btn_choose_profile = QPushButton(translate("member.choose_profile"))
        self.btn_remove_profile = QPushButton(translate("member.remove_profile"))
        profile_btn_layout.addWidget(self.btn_choose_profile)
        profile_btn_layout.addWidget(self.btn_remove_profile)

        form_layout.addRow(translate("member.member_no"), self.member_no_input)
        form_layout.addRow(translate("member.first_name"), self.first_name_input)
        form_layout.addRow(translate("member.last_name"), self.last_name_input)
        form_layout.addRow(translate("member.email"), self.email_input)
        form_layout.addRow(translate("member.phone"), self.phone_input)
        form_layout.addRow(translate("member.profile_photo"), self.profile_preview)
        form_layout.addRow("", profile_btn_layout)
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
        self.btn_choose_profile.clicked.connect(self._on_choose_profile)
        self.btn_remove_profile.clicked.connect(self._on_remove_profile)

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

            # Préparer les données
            result_data = {
                "member_no": member_no,
                "last_name": self.last_name_input.text().strip(),
                "first_name": self.first_name_input.text().strip(),
                "email": self.email_input.text().strip() or None,
                "phone": self.phone_input.text().strip() or None,
                "is_active": self.active_input.isChecked(),
                "profile_image": None,  # Sera updaté après
            }

            # Traiter la photo de profil
            if hasattr(self, "_new_profile_path") and self._new_profile_path is not None:
                if self._new_profile_path == "":
                    result_data["profile_image"] = None  # Suppression
                else:
                    result_data["profile_image"] = self._new_profile_path  # Nouvelle photo

            # PATTERN BookEditor : utiliser session context manager
            with get_session() as session:
                if self._member:
                    # Mode édition : MERGE l'objet existant
                    member_to_update = session.merge(self._member)
                    for key, value in result_data.items():
                        setattr(member_to_update, key, value)
                else:
                    # Mode création : créer un nouveau
                    member = Member(**result_data)
                    session.add(member)

                # Commit AVANT de fermer la session
                session.commit()

            # Fermer le dialogue APRÈS la session
            super().accept()

        except Exception as e:
            print(f"[DEBUG] Sauvegarde échouée: {e}")
            import traceback

            traceback.print_exc()

            QMessageBox.critical(
                self,
                translate("member_editor.error_title"),
                f"{translate('member_editor.error_save')}: {str(e)}",
            )

    def _on_choose_profile(self):
        """Ouvre un dialogue pour choisir une photo de profil."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            translate("member.select_profile_image"),
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if file_path:
            self._process_profile_image(file_path)

    def _process_profile_image(self, source_path: str):
        """
        Redimensionne et copie la photo de profil.

        Args:
            source_path: Chemin vers l'image source sélectionnée
        """
        try:
            # Générer nom unique
            ext = Path(source_path).suffix
            new_filename = f"{uuid.uuid4()}{ext}"
            dest_path = user_profile_images_dir() / new_filename

            # Redimensionner à 800x800 max (conserver ratio)
            img = Image.open(source_path)
            img.thumbnail((800, 800), Image.Resampling.LANCZOS)
            img.save(dest_path, quality=95)

            # Mettre à jour preview (128x128)
            pixmap = QPixmap(str(dest_path))
            scaled_pixmap = pixmap.scaled(
                128,
                128,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.profile_preview.setPixmap(scaled_pixmap)

            # Stocker le chemin
            self._new_profile_path = str(dest_path)

        except Exception as e:
            QMessageBox.warning(
                self,
                translate("errors.image_processing"),
                f"{translate('errors.failed_to_process_image')}: {str(e)}",
            )

    def _on_remove_profile(self):
        """Supprime la photo de profil."""
        self.profile_preview.clear()
        self._new_profile_path = None

        # Si on édite un membre existant, marquer pour suppression
        if self._member and self._member.profile_image:
            self._new_profile_path = ""  # String vide = suppression
