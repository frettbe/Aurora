"""Panneau de détails pour l'affichage d'informations complètes sur un livre.

Ce module définit BookDetailsPanel, un widget qui affiche la couverture,
le titre, l'auteur, le résumé et autres détails d'un livre sélectionné.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from ..persistence.models_sa import Book
from ..services.translation_service import translate
from ..utils.paths import user_covers_dir


class BookDetailsPanel(QWidget):
    """Widget d'affichage des détails complets d'un livre."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialise le panneau de détails livre.

        Args:
            parent: Widget parent optionnel.
        """
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Construit l'interface utilisateur du panneau."""
        layout = QVBoxLayout(self)

        # Label couverture (256x256)
        self.cover_label = QLabel(self)
        self.cover_label.setFixedSize(256, 256)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setStyleSheet("border: 1px solid #ccc;")
        layout.addWidget(self.cover_label, alignment=Qt.AlignmentFlag.AlignCenter)

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

    def _load_placeholder_book(self) -> QPixmap:
        """Charge l'image placeholder pour les livres.

        Returns:
            QPixmap: Image placeholder ou pixmap gris par défaut.
        """

        placeholder_path = (
            Path(__file__).parent.parent / "resources" / "icons" / "app" / "placeholder-book.svg"
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

    def update_from_book(self, book: Book | None) -> None:
        """Met à jour le panneau avec les données d'un livre.

        Args:
            book: Instance Book à afficher, ou None pour effacer.
        """
        if book is None:
            self.clear()
            return

        # Charger la couverture
        if book.cover_image:
            # Retirer le préfixe 'covers/' si présent
            cover_filename = book.cover_image.replace("covers/", "")
            cover_path = user_covers_dir() / cover_filename

            if cover_path.exists():
                pixmap = QPixmap(str(cover_path))
                scaled = pixmap.scaled(
                    256,
                    256,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.cover_label.setPixmap(scaled)
            else:
                # 🎯 NOUVEAU : Afficher placeholder au lieu de texte
                self.cover_label.setPixmap(self._load_placeholder_book())
        else:
            # 🎯 NOUVEAU : Afficher placeholder au lieu de texte
            self.cover_label.setPixmap(self._load_placeholder_book())

        # Afficher les infos
        info_text = f"""
        <h2>{book.title or ''}</h2>
        <p><b>{translate('book_details.author')}:</b> {book.authors_text or 'N/A'}</p>
        <p><b>{translate('book_details.year')}:</b> {book.year or 'N/A'}</p>
        <p><b>{translate('book_details.publisher')}:</b> {book.publisher or 'N/A'}</p>
        <p><b>{translate('book_details.isbn')}:</b> {book.isbn or 'N/A'}</p>
        <hr>
        <p><b>{translate('book_details.summary')}:</b></p>
        <p>{book.summary or translate('book_details.no_summary')}</p>
        """
        self.info_label.setText(info_text)

    def clear(self) -> None:
        """Efface le panneau (placeholder)."""
        self.cover_label.setPixmap(self._load_placeholder_book())
        self.info_label.setText(translate("book_details.no_selection"))
