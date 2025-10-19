"""Fenêtre de dialogue pour la création et l'édition d'une fiche Livre.

Ce module contient la classe `BookEditor`, qui est un formulaire complet
permettant de renseigner toutes les informations d'un livre. Il inclut
également une logique de complétion automatique via les services externes (BnF).
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..persistence.database import get_session
from ..persistence.models_sa import Book
from ..services.bnf_adapter import BnfAdapter
from ..services.translation_service import translate
from ..utils.paths import user_covers_dir, user_data_dir
from .bnf_select_dialog import BnfNotice, BnfSelectDialog


def _to_int(val: Any, default: int = 0) -> int:
    """Tente de convertir une valeur en entier de manière sécurisée.

    Utile pour les widgets comme QSpinBox qui attendent un entier,
    même si la donnée source est une chaîne, None, ou autre.

    Args:
        val: La valeur à convertir.
        default: La valeur à retourner en cas d'échec de la conversion.

    Returns:
        L'entier converti ou la valeur par défaut.
    """
    try:
        if val is None:
            return default
        s = str(val).strip()
        if s:  # chaîne non vide
            return int(s)
        return default  # chaîne vide ⇒ fallback
    except (ValueError, TypeError):
        return default


class BookEditor(QDialog):
    """Dialogue modal pour créer ou modifier un livre.

    En mode "création" (`book` is None), le formulaire est vide.
    En mode "édition", il est pré-rempli avec les données du livre.

    Après validation, les données sont disponibles dans `self.result_data`.
    """

    def __init__(self, parent: QWidget | None = None, book: Book | None = None):
        """Initialise l'éditeur.

        Args:
            parent: Le widget parent.
            book: L'objet Book à éditer. Si None, la fenêtre est en mode création.
        """
        super().__init__(parent)
        self.setWindowTitle(
            translate("book_editor.window_edit") if book else translate("book_editor.window_new")
        )

        self._book = book
        self.result_data: dict[str, Any] = {}

        main_layout = QVBoxLayout(self)

        def create_form_row(label: str, widget: QWidget) -> QWidget:
            """Crée une ligne de formulaire (Label + Widget) et l'ajoute au layout."""
            row_layout = QHBoxLayout()
            row_layout.addWidget(QLabel(label))
            row_layout.addWidget(widget)
            main_layout.addLayout(row_layout)
            return widget

        # --- Champs du formulaire ---
        self.ed_code = create_form_row(translate("book_editor.label_code"), QLineEdit())

        self.sp_volume = QSpinBox()
        self.sp_volume.setRange(0, 9999)
        create_form_row(translate("book_editor.label_volume"), self.sp_volume)

        self.ed_isbn = create_form_row(translate("book_editor.label_isbn"), QLineEdit())
        self.ed_title = create_form_row(translate("book_editor.label_title"), QLineEdit())
        self.ed_author = create_form_row(translate("book_editor.label_author"), QLineEdit())
        self.ed_publisher = create_form_row(translate("book_editor.label_publisher"), QLineEdit())

        self.sp_year = QSpinBox()
        self.sp_year.setRange(0, 9999)
        create_form_row(translate("book_editor.label_year"), self.sp_year)

        self.ed_fund = create_form_row(translate("book_editor.label_fund"), QLineEdit())

        self.sp_total = QSpinBox()
        self.sp_total.setRange(0, 9999)
        self.sp_total.setValue(1)
        create_form_row(translate("book_editor.label_copies_total"), self.sp_total)

        self.sp_avail = QSpinBox()
        self.sp_avail.setRange(0, 9999)
        self.sp_avail.setValue(1)
        create_form_row(translate("book_editor.label_copies_available"), self.sp_avail)

        # 🆕 NOUVEAU : Champ résumé (QTextEdit multiligne)
        self.ed_summary = QTextEdit()
        self.ed_summary.setPlaceholderText(translate("book_editor.summary_placeholder"))
        self.ed_summary.setMaximumHeight(100)  # Limite la hauteur (environ 4-5 lignes)
        create_form_row(translate("book_editor.label_summary"), self.ed_summary)

        # === COUVERTURE ===
        # Container horizontal pour preview + boutons
        cover_widget = QWidget()
        cover_hlayout = QHBoxLayout(cover_widget)
        cover_hlayout.setContentsMargins(0, 0, 0, 0)

        # Miniature preview
        self.cover_preview = QLabel()
        self.cover_preview.setFixedSize(64, 64)
        self.cover_preview.setAlignment(Qt.AlignCenter)
        self.cover_preview.setStyleSheet("border: 1px solid #ccc; background-color: #f0f0f0;")
        self.cover_preview.setText("📚")
        cover_hlayout.addWidget(self.cover_preview)

        # Boutons
        self.btn_add_cover = QPushButton(translate("book_editor.cover_add_button"))
        self.btn_add_cover.clicked.connect(self._on_add_cover)
        cover_hlayout.addWidget(self.btn_add_cover)

        self.btn_remove_cover = QPushButton(translate("book_editor.cover_remove_button"))
        self.btn_remove_cover.clicked.connect(self._on_remove_cover)
        self.btn_remove_cover.setEnabled(False)
        cover_hlayout.addWidget(self.btn_remove_cover)

        cover_hlayout.addStretch()

        # Ajoute au formulaire en utilisant create_form_row
        create_form_row(translate("book_editor.cover_label"), cover_widget)

        # Variable pour stocker le chemin
        self.current_cover_path: str | None = None

        # --- Pré-remplissage si édition ---
        if book:
            self._fill_form_from_book(book)

        # --- Boutons d'action ---
        buttons_layout = QHBoxLayout()
        self.btn_bnf = QPushButton(translate("buttons.bnf_complete"))
        self.btn_ok = QPushButton(translate("buttons.save"))
        self.btn_cancel = QPushButton(translate("buttons.cancel"))

        buttons_layout.addWidget(self.btn_bnf)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btn_ok)
        buttons_layout.addWidget(self.btn_cancel)

        main_layout.addLayout(buttons_layout)

        # --- Connexion des signaux ---
        self.btn_ok.clicked.connect(self._on_accept)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_bnf.clicked.connect(self._on_complete_from_bnf)

    def _fill_form_from_book(self, book: Book):
        """Remplit les champs du formulaire avec les données d'un objet Book."""
        self.ed_code.setText(getattr(book, "code", "") or "")
        self.ed_isbn.setText(getattr(book, "isbn", "") or "")
        self.ed_title.setText(getattr(book, "title", "") or "")
        self.ed_author.setText(getattr(book, "author", "") or "")
        self.ed_publisher.setText(getattr(book, "publisher", "") or "")
        self.ed_fund.setText(getattr(book, "fund", "") or "")

        self.sp_volume.setValue(_to_int(getattr(book, "volume", None), 0))
        self.sp_year.setValue(_to_int(getattr(book, "year", None), 0))
        self.sp_total.setValue(_to_int(getattr(book, "copies_total", None), 1))
        self.sp_avail.setValue(_to_int(getattr(book, "copies_available", None), 1))

        # 🆕 NOUVEAU : Chargement du résumé
        self.ed_summary.setPlainText(getattr(book, "summary", "") or "")

        # Charge couverture si présente
        self.current_cover_path = getattr(book, "cover_image", None)
        self._update_cover_preview()
        if self.current_cover_path:
            self.btn_remove_cover.setEnabled(True)

        # Sélectionne la bonne catégorie dans la ComboBox
        category_to_select = getattr(book, "category", None)
        if category_to_select:
            index = self.cb_category.findData(category_to_select)
            if index >= 0:
                self.cb_category.setCurrentIndex(index)

    def _on_accept(self):
        """Valide les données saisies et ferme le dialogue si elles sont valides."""
        title = self.ed_title.text().strip()
        if not title:
            QMessageBox.warning(
                self,
                translate("messages.validation_title"),
                translate("messages.validation_missing_title"),
            )
            return

        total = self.sp_total.value()
        avail = self.sp_avail.value()
        if avail > total:
            QMessageBox.warning(
                self,
                translate("messages.validation_title"),
                translate("messages.validation_invalid_copies_count"),
            )
            return

        # Prépare le dictionnaire de résultats pour la MainWindow
        year_value = self.sp_year.value()
        self.result_data = {
            "code": self.ed_code.text().strip() or None,
            "volume": self.sp_volume.value() if self.sp_volume.value() != 0 else None,
            "isbn": self.ed_isbn.text().strip() or None,
            "title": title,
            "author": self.ed_author.text().strip() or None,
            "publisher": self.ed_publisher.text().strip() or None,
            "year": year_value if year_value != 0 else None,
            "collection": self.ed_fund.text().strip() or None,
            "copies_total": total,
            "copies_available": avail,
            "summary": self.ed_summary.toPlainText().strip() or None,
            "cover_image": self.current_cover_path,
        }

        with get_session() as session:
            if self._book:  # Mode édition
                # Mettre à jour l'objet existant
                book_to_update = session.merge(self._book)
                for key, value in self.result_data.items():
                    setattr(book_to_update, key, value)
            else:  # Mode création
                # Créer un nouveau livre
                new_book = Book(**self.result_data)
                session.add(new_book)

            session.commit()

        self.accept()

    def _apply_if_empty(self, field_widget: QWidget, value: str | None):
        """Remplit un champ (QLineEdit, QSpinBox ou QTextEdit) seulement s'il est vide."""
        if value is None:
            return

        if isinstance(field_widget, QLineEdit) and not field_widget.text().strip():
            field_widget.setText(value)
        elif isinstance(field_widget, QSpinBox) and field_widget.value() == 0:
            field_widget.setValue(_to_int(value))
        elif (
            isinstance(field_widget, QTextEdit) and not field_widget.toPlainText().strip()
        ):  # 🆕 NOUVEAU
            field_widget.setPlainText(value)

    def _on_complete_from_bnf(self):
        """Tente de compléter les champs vides en interrogeant l'API de la BnF.

        La recherche se fait en priorité par ISBN. En cas d'échec ou si l'ISBN
        est vide, une recherche par titre/auteur est effectuée. Si plusieurs
        résultats sont trouvés, le dialogue `BnfSelectDialog` est utilisé.
        """
        isbn = self.ed_isbn.text().strip()
        title = self.ed_title.text().strip()
        author = self.ed_author.text().strip()

        try:
            adapter = BnfAdapter()
            notice: BnfNotice | None = None

            if isbn:
                notice = adapter.by_isbn(isbn)

            # Si pas de résultat par ISBN ou pas d'ISBN, on tente titre/auteur
            if not notice and (title or author):
                hits = adapter.search_title_author(title, author)
                if not hits:
                    QMessageBox.information(
                        self, translate("bnf_search.title"), translate("bnf_search.no_results")
                    )
                    return
                elif len(hits) == 1:
                    notice = hits[0]
                else:
                    # Plusieurs résultats : on demande à l'utilisateur de choisir
                    select_dialog = BnfSelectDialog(self, items=hits)
                    if select_dialog.exec():
                        notice = select_dialog.selected_notice
                    else:
                        return  # L'utilisateur a annulé

            # Si on a obtenu une notice, on remplit les champs vides
            if notice:
                self._apply_if_empty(self.ed_title, notice.get("title"))
                self._apply_if_empty(self.ed_author, notice.get("author"))
                self._apply_if_empty(self.ed_publisher, notice.get("publisher"))
                self._apply_if_empty(self.sp_year, notice.get("year"))
                # 🆕 NOUVEAU : Remplir le résumé depuis la BnF (si disponible)
                self._apply_if_empty(self.ed_summary, notice.get("summary"))

                # On remplit l'ISBN seulement s'il était vide au départ
                if not isbn and (new_isbn := notice.get("isbn")):
                    self.ed_isbn.setText(new_isbn)
            else:
                QMessageBox.information(
                    self, translate("bnf_search.title"), translate("bnf_search.no_results")
                )

        except Exception as e:
            QMessageBox.warning(
                self,
                translate("bnf_search.error_title"),
                translate("bnf_search.error_message").format(error=str(e)),
            )

    def _on_add_cover(self) -> None:
        """Ouvre dialogue pour sélectionner une image de couverture."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            translate("book_editor.cover_dialog_title"),
            "",
            translate("book_editor.cover_dialog_filter"),
        )

        if not file_path:
            return  # Annulé

        source_path = Path(file_path)

        # Génère nom unique : {book_id}_{uuid}.ext
        book_id = self._book.id if self._book and self._book.id else "new"
        unique_name = f"{book_id}_{uuid.uuid4().hex[:8]}{source_path.suffix.lower()}"
        dest_path = user_covers_dir() / unique_name

        try:
            # Redimensionne et sauvegarde
            self._resize_and_save_cover(source_path, dest_path)

            # Stocke chemin relatif
            self.current_cover_path = f"covers/{unique_name}"

            # Met à jour preview
            self._update_cover_preview()

            # Active bouton suppression
            self.btn_remove_cover.setEnabled(True)

        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Impossible d'ajouter la couverture : {e}")

    def _on_remove_cover(self) -> None:
        """Supprime la couverture actuelle."""
        if not self.current_cover_path:
            return

        # Supprime fichier physique
        cover_full_path = user_data_dir() / self.current_cover_path
        if cover_full_path.exists():
            cover_full_path.unlink()

        # Réinitialise
        self.current_cover_path = None
        self.cover_preview.clear()
        self.cover_preview.setText("📚")
        self.btn_remove_cover.setEnabled(False)

    def _resize_and_save_cover(self, source: Path, dest: Path, max_size: int = 800) -> None:
        """Redimensionne l'image si trop grande et sauvegarde.

        Args:
            source: Chemin de l'image source
            dest: Chemin de destination
            max_size: Taille maximale en pixels (largeur ou hauteur)
        """
        try:
            from PIL import Image
        except ImportError:
            # Si Pillow pas installé, copie sans redimensionner
            import shutil

            shutil.copy(source, dest)
            return

        img = Image.open(source)

        # Redimensionne si nécessaire
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        # Convertit en RGB si nécessaire (pour JPEG)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # Sauvegarde optimisée
        img.save(dest, optimize=True, quality=85)

    def _update_cover_preview(self) -> None:
        """Met à jour la miniature de prévisualisation."""
        if not self.current_cover_path:
            self.cover_preview.clear()
            self.cover_preview.setText("📚")
            return

        cover_full_path = user_data_dir() / self.current_cover_path
        if not cover_full_path.exists():
            self.cover_preview.setText("❌")
            return

        pixmap = QPixmap(str(cover_full_path))
        if pixmap.isNull():
            self.cover_preview.setText("❌")
            return

        # Redimensionne pour preview 64x64
        scaled_pixmap = pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.cover_preview.setPixmap(scaled_pixmap)
