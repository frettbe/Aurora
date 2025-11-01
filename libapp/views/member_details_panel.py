"""Panneau de détails pour l'affichage d'informations complètes sur un membre.

Ce module définit MemberDetailsPanel, un widget qui affiche la photo,
le nom, l'email, le téléphone et autres détails d'un membre sélectionné.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from ..persistence.models_sa import Member
from ..services.translation_service import translate


class MemberDetailsPanel(QWidget):
    """Widget d'affichage des détails complets d'un membre."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialise le panneau de détails membre.

        Args:
            parent: Widget parent optionnel.
        """
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Construit l'interface utilisateur du panneau."""
        layout = QVBoxLayout(self)

        # Label photo (256x256)
        self.photo_label = QLabel(self)
        self.photo_label.setFixedSize(256, 256)
        self.photo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.photo_label.setStyleSheet("border: 1px solid #ccc;")
        layout.addWidget(self.photo_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Scroll area pour texte
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.info_label = QLabel(self)
        self.info_label.setWordWrap(True)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.info_label)

        layout.addWidget(scroll)

        # Placeholder par défaut
        self.clear()

    def _load_placeholder_member(self) -> QPixmap:
        """Charge l'image placeholder pour les membres.

        Returns:
            QPixmap: Image placeholder ou pixmap gris par défaut.
        """
        from pathlib import Path

        placeholder_path = (
            Path(__file__).parent.parent / "resources" / "icons" / "app" / "placeholder-avatar.svg"
        )

        if placeholder_path.exists():
            pixmap = QPixmap(str(placeholder_path))
            if not pixmap.isNull():
                return pixmap.scaled(
                    256,
                    256,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

        # Fallback : pixmap gris
        pixmap = QPixmap(256, 256)
        pixmap.fill(Qt.GlobalColor.lightGray)
        return pixmap

    def update_from_member(self, member: Member | None) -> None:
        """Met à jour le panneau avec les données d'un membre.

        Args:
            member: Instance Member à afficher, ou None pour effacer.
        """
        if member is None:
            self.clear()
            return

        # Afficher placeholder au lieu de texte
        self.photo_label.setPixmap(self._load_placeholder_member())

        # Afficher les infos
        active_status = (
            translate("member_details.active")
            if member.is_active
            else translate("member_details.inactive")
        )

        if member.profile_image and Path(member.profile_image).exists():
            pixmap = QPixmap(member.profile_image)
            scaled_pixmap = pixmap.scaled(
                256,
                256,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.photo_label.setPixmap(scaled_pixmap)
        else:
            # Charger le placeholder avatar
            self._load_placeholder_member()

        info_text = f"""
        <h2>{member.first_name} {member.last_name}</h2>
        <p><b>{translate('member_details.member_no')}:</b> {member.member_no or 'N/A'}</p>
        <p><b>{translate('member_details.email')}:</b> {member.email or 'N/A'}</p>
        <p><b>{translate('member_details.phone')}:</b> {member.phone or 'N/A'}</p>
        <p><b>{translate('member_details.active_status')}:</b> {active_status}</p>
        <p><b>{translate('member_details.date_joined')}:</b> {member.date_joined or 'N/A'}</p>
        """
        self.info_label.setText(info_text)

    def clear(self) -> None:
        """Efface le panneau (placeholder)."""
        self.photo_label.setPixmap(self._load_placeholder_member())
        self.info_label.setText(translate("member_details.no_selection"))
