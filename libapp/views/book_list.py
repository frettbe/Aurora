"""

Vue principale affichant la liste des livres de la bibliothèque.

"""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QByteArray, QModelIndex, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QProgressDialog,
    QTableView,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select

from ..persistence.database import get_session
from ..persistence.models_sa import Book
from ..services.audit_service import audit_book_created, audit_book_deleted, audit_book_updated
from ..services.export_service import ExportMetadata, export_data
from ..services.meta_search_service import BestResultStrategy, MetaSearchService
from ..services.preferences import Preferences, save_preferences
from ..services.translation_service import translate
from .export_dialog import ExportDialog
from .natural_sort_proxy import NaturalSortProxyModel


class BookTableModel(QAbstractTableModel):
    """Modèle de données Qt pour la table des livres."""

    # 🎯 Toutes les colonnes disponibles (identifiant: label par défaut)
    ALL_COLUMNS = {
        "id": "ID",
        "code": "Code",
        "title": "Titre",
        "volume": "Tome",
        "author": "Auteurs",
        "year": "Année",
        "isbn": "ISBN",
        "publisher": "Éditeur",
        "fund": "Fonds",
        "available": "Disponible",
        "summary": "Résumé",
        "cover_image": translate("column.cover_image"),
    }

    def __init__(self, visible_columns: list[str] | None = None):
        super().__init__()
        self._all_books: list[Book] = []

        # Colonnes visibles (par défaut = toutes)
        if visible_columns is None:
            visible_columns = list(self.ALL_COLUMNS.keys())
        self._visible_columns = visible_columns

        # Headers affichés basés sur les colonnes visibles
        self._column_headers = [self.ALL_COLUMNS[col] for col in self._visible_columns]

    def set_books(self, books: list[Book]):
        self.beginResetModel()
        self._all_books = list(books)
        self._filtered_books = list(books)
        self.endResetModel()

    def apply_filter(self, search_text: str):
        search_term = (search_text or "").strip().lower()
        self.beginResetModel()
        if not search_term:
            self._filtered_books = list(self._all_books)
        else:
            self._filtered_books = [
                book
                for book in self._all_books
                if search_term in (book.title or "").lower()
                or search_term in (book.authors_text or "").lower()
                or search_term in (book.isbn or "").lower()
            ]
        self.endResetModel()

    def get_book_by_row(self, row: int) -> Book | None:
        if 0 <= row < len(self._filtered_books):
            return self._filtered_books[row]
        return None

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._filtered_books)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._visible_columns)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        """Données d'une cellule."""
        if not index.isValid():
            return None
        if not (0 <= index.row() < len(self._filtered_books)):
            return None
        if not (0 <= index.column() < len(self._visible_columns)):
            return None
        book = self._filtered_books[index.row()]
        col_name = self._visible_columns[index.column()]

        if role == Qt.ItemDataRole.DisplayRole:
            # 🎯 Mapping identifiant colonne → donnée
            if col_name == "id":
                return str(book.id)
            elif col_name == "code":
                return book.code or ""
            elif col_name == "title":
                return book.title or "(sans titre)"
            elif col_name == "volume":
                return book.volume or 1
            elif col_name == "author":
                return book.author or ""
            elif col_name == "year":
                return str(book.year) if book.year else ""
            elif col_name == "isbn":
                return book.isbn or ""
            elif col_name == "publisher":
                return book.publisher or ""
            elif col_name == "fund":
                return book.fund or ""
            elif col_name == "available":
                return f"{book.copies_available}/{book.copies_total}"
            elif col_name == "summary":
                return (book.summary or "")[:50] + ("..." if len(book.summary or "") > 50 else "")
            elif col_name == "cover_image":
                # Pas d'affichage texte pour les images
                return ""

        elif role == Qt.ItemDataRole.DecorationRole:
            # Affichage des icônes/images dans les cellules
            if col_name == "cover_image":
                from PySide6.QtGui import QPixmap

                from ..utils.paths import user_data_dir

                cover_path = getattr(book, "cover_image", None)
                if cover_path:
                    full_path = user_data_dir() / cover_path
                    if full_path.exists():
                        pixmap = QPixmap(str(full_path))
                        # Miniature 32x32
                        return pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            return None

        elif role == Qt.ItemDataRole.UserRole:
            # Retourner l'objet book complet
            return book

        return None

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole
    ) -> str | None:
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            if 0 <= section < len(self._column_headers):
                return self._column_headers[section]  # ← Utiliser section !
        return None

    def get_book_at(self, row: int) -> Book:
        """Retourne le livre à la ligne donnée."""
        return self._filtered_books[row]


class BookListView(QWidget):
    """Widget principal pour afficher et interagir avec la liste des livres."""

    bookActivated = Signal(int)
    requestDelete = Signal(int)

    def __init__(self, parent: QWidget, prefs: Preferences):
        super().__init__(parent)
        self._prefs = prefs
        self._setup_ui()
        self._connect_signals()
        self.load_view_state()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel(translate("book_list.search_label")))
        self.search_input = QLineEdit()
        self.search_input.setClearButtonEnabled(True)
        filter_layout.addWidget(self.search_input)
        layout.addLayout(filter_layout)
        self.table_view = QTableView()
        visible_columns = self._prefs.books_visible_columns
        self.table_model = BookTableModel(visible_columns=visible_columns)
        self.proxy_model = NaturalSortProxyModel()
        self.proxy_model.setSourceModel(self.table_model)
        self.table_view.setModel(self.proxy_model)
        self.table_view.setSortingEnabled(True)
        self.table_view.horizontalHeader().setStretchLastSection(False)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        layout.addWidget(self.table_view)

    def _connect_signals(self):
        self.search_input.textChanged.connect(self._on_filter_changed)
        self.table_view.doubleClicked.connect(self._on_double_clicked)

    # --- MÉTHODES MODIFIÉES POUR LE DÉBOGAGE ---

    def load_view_state(self):
        """
        Charge l'état de la vue (colonnes) depuis les préférences.
        Le filtre est temporairement désactivé pour le test.
        """
        state = self._prefs.books_view_state or {}

        # On vide la barre de recherche au lieu de charger l'ancienne valeur
        self.search_input.blockSignals(True)
        self.search_input.setText("")
        self.search_input.blockSignals(False)

        # On charge toujours l'état des colonnes
        if header_state := state.get("header_state"):
            self.table_view.horizontalHeader().restoreState(
                QByteArray.fromBase64(header_state.encode("ascii"))
            )

    def save_view_state(self):
        """Sauvegarde l'état actuel de la vue dans les préférences."""
        state = {
            "search_text": self.search_input.text(),
            "header_state": self.table_view.horizontalHeader()
            .saveState()
            .toBase64()
            .data()
            .decode("ascii"),
        }
        self._prefs.books_view_state = state
        save_preferences(self._prefs)

    @Slot()
    def refresh(self):
        """Recharge les données depuis la BDD et applique le filtre."""
        with get_session() as session:
            result = session.scalars(select(Book).order_by(Book.title)).all()

            # 🔧 FIX CRITIQUE : Détacher les objets AVANT la fermeture de la session
            books = []
            for book in result:
                session.expunge(book)  # Détache l'objet de la session
                books.append(book)

        # Maintenant la session est fermée, mais les objets sont accessibles
        self.table_model.set_books(books)
        self._on_filter_changed()
        # Auto-resize des colonnes
        self.table_view.resizeColumnsToContents()

        # Ajouter un minimum pour lisibilité
        for col in range(self.table_view.model().columnCount()):
            width = self.table_view.columnWidth(col)
            self.table_view.setColumnWidth(col, max(width, 80))

        # Étendre la dernière colonne
        self.table_view.horizontalHeader().setStretchLastSection(True)

    @Slot()
    def _on_filter_changed(self):
        self.table_model.apply_filter(self.search_input.text())
        self.save_view_state()

    @Slot(QModelIndex)
    def _on_double_clicked(self, index: QModelIndex):
        """Ouvre l'édition du livre au double-clic."""
        if not index.isValid():
            return
        source_index = self.proxy_model.mapToSource(index)
        if not source_index.isValid():
            return
        book = self.table_model.get_book_by_row(source_index.row())
        if book:
            self.bookActivated.emit(book.id)

    def contextMenuEvent(self, event):
        if not self.table_view.selectionModel().hasSelection():
            return

        # Créer le menu contextuel
        menu = QMenu(self)

        # Ajouter les actions
        edit_action = menu.addAction(translate("context.edit"))
        edit_action.triggered.connect(self._on_edit)

        delete_action = menu.addAction(translate("context.delete"))
        delete_action.triggered.connect(self._on_delete)

        menu.addSeparator()

        borrow_action = menu.addAction(translate("context.borrow"))
        borrow_action.triggered.connect(self._on_borrow)

        return_action = menu.addAction(translate("context.return"))
        return_action.triggered.connect(self._on_return)

        menu.addSeparator()

        export_action = menu.addAction(translate("context.export"))
        export_action.triggered.connect(self._on_export)

        menu.addSeparator()

        bnf_action = menu.addAction(translate("context.open_bnf"))
        bnf_action.triggered.connect(self._on_open_bnf)

        new_book_action = menu.addAction(translate("context.new_book"))
        new_book_action.triggered.connect(self._on_new_book)

        # Afficher le menu
        menu.exec(event.globalPos())

    # Ajouter les méthodes stubs (pour l'instant) :
    def _on_edit(self):
        """Ouvre l'éditeur pour modifier le livre sélectionné."""
        selection = self.table_view.selectionModel().selectedRows()
        if not selection:
            return

        source_index = self.proxy_model.mapToSource(selection[0])
        book = self.table_model._filtered_books[source_index.row()]

        # Sauvegarder l'état avant modification
        old_title = book.title

        from .book_editor import BookEditor

        dialog = BookEditor(self, book=book)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

            # 🎯 AUDIT : Logger la modification
            audit_book_updated(
                book_id=book.id,
                changes={"old_title": old_title, "new_title": book.title},
                user="system",
            )

    def _on_delete(self):
        """Supprime le livre sélectionné."""
        selection = self.table_view.selectionModel().selectedRows()
        if not selection:
            return

        source_index = self.proxy_model.mapToSource(selection[0])
        book = self.table_model._filtered_books[source_index.row()]

        # Sauvegarder les infos avant suppression
        book_id = book.id
        book_title = book.title or "(sans titre)"

        # Dialogue de confirmation
        reply = QMessageBox.question(
            self,
            translate("book_list.delete_title"),
            translate("book_list.delete_confirm", title=book_title),
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            try:
                with get_session() as session:
                    book_to_delete = session.get(Book, book_id)
                    if book_to_delete:
                        session.delete(book_to_delete)
                        session.commit()

                self.refresh()

                # 🎯 AUDIT : Logger la suppression
                audit_book_deleted(book_id=book_id, title=book_title, user="system")

                QMessageBox.information(
                    self,
                    translate("book_list.delete_success_title"),
                    translate("book_list.delete_success_body"),
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    translate("errors.delete_book_title"),
                    translate("errors.delete_book_body", error=str(e)),
                )

    def _on_borrow(self):
        """Emprunter le livre sélectionné."""
        selected_rows = self.table_view.selectionModel().selectedRows()
        if not selected_rows:
            return

        source_index = self.proxy_model.mapToSource(selected_rows[0])
        book_index = source_index.row()
        book = self.table_model.get_book_by_row(book_index)

        if not book or book.copies_available <= 0:
            QMessageBox.warning(
                self, translate("book_list.borrow_impossible"), translate("book_list.borrow_not_av")
            )
            return

        from .loan_dialog import LoanDialog

        dialog = LoanDialog(self, book=book)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            QMessageBox.information(
                self,
                translate("book_list.borrow_success_title"),
                translate("book_list.borrow_success_message"),
            )

    def _on_return(self):
        """Retourner le livre sélectionné."""
        selected_rows = self.table_view.selectionModel().selectedRows()
        if not selected_rows:
            return

        source_index = self.proxy_model.mapToSource(selected_rows[0])
        book = self.table_model.get_book_by_row(source_index.row())
        if not book:
            return

        # Trouver le prêt ouvert pour ce livre
        from ..persistence.models_sa import Loan, LoanStatus

        preselected_loan_id = None
        with get_session() as session:
            open_loan = session.execute(
                select(Loan).where(Loan.book_id == book.id, Loan.status == LoanStatus.open).limit(1)
            ).scalar_one_or_none()

            if open_loan:
                preselected_loan_id = open_loan.id

        if not preselected_loan_id:
            QMessageBox.information(
                self,
                translate("book_list.no_open_loan_title"),
                translate("book_list.no_open_loan_message"),
            )
            return

        # Ouvrir le dialogue avec présélection
        from .loan_dialogs import ReturnLoanDialog

        dialog = ReturnLoanDialog(self, preselected_loan_id=preselected_loan_id)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_loan_id:
            from ..services.loan_service import return_loan as service_return

            service_return(dialog.selected_loan_id)
            self.refresh()

    def create_native_progress(self):
        """Progress bar qui respecte automatiquement le thème qdarkstyle actuel"""
        progress = QProgressDialog(self)
        progress.setWindowTitle(translate("book_list.search_bnf_title"))
        progress.setLabelText(translate("book_list. search_in_progress"))
        progress.setRange(0, 100)
        progress.setValue(0)
        progress.setMinimumWidth(400)
        progress.setMinimumHeight(120)

        # 🎨 PAS de style custom - qdarkstyle gère automatiquement !
        # Centrage sur fenêtre parent
        self.center_dialog_on_parent(progress)
        return progress

    def center_dialog_on_parent(self, dialog):
        """Centre une dialog sur la fenêtre principale"""
        parent_rect = self.geometry()
        dialog_rect = dialog.geometry()
        x = parent_rect.x() + (parent_rect.width() - dialog_rect.width()) // 2
        y = parent_rect.y() + (parent_rect.height() - dialog_rect.height()) // 2
        dialog.move(x, y)

    def _on_open_bnf(self):
        """Enrichir les données via recherche BnF/multi-sources."""
        selected_rows = self.table_view.selectionModel().selectedRows()
        if not selected_rows:
            return

        proxy_index = selected_rows[0]
        source_index = self.proxy_model.mapToSource(proxy_index)
        book_index = source_index.row()

        book = self.table_model.get_book_by_row(book_index)
        if not book:
            return

        # Initialiser le service de recherche avec stratégie avancée
        metaservice = MetaSearchService(strategy=BestResultStrategy())

        # 🔥 PROGRESS BAR
        progress = self.create_native_progress()
        progress.show()

        try:
            searchresults = []

            # ÉTAPE 1
            if book.isbn and book.isbn.strip():
                progress.setLabelText(translate("book_list.search_isbn"))
                progress.setValue(20)
                QApplication.processEvents()

                searchresults.extend(metaservice.search_by_isbn(book.isbn.strip(), {}))
                progress.progress.setValue(60)
                QApplication.processEvents()

            # ÉTAPE 2
            if not searchresults and book.title:
                progress.setLabelText(translate("book_list.search_title_author"))
                progress.setValue(80)

                author_text = book.authors_text or ""
                searchresults.extend(
                    metaservice.search_by_title_author(book.title, author_text, {})
                )

            progress.setLabelText(translate("book_list.search_completed"))
            progress.setValue(100)
            QApplication.processEvents()

            # Petit délai pour voir le "TERMINÉ"
            import time

            time.sleep(0.5)

            # 3. Affichage des résultats
            if not searchresults:
                QMessageBox.information(
                    self,
                    "Recherche",
                    "Aucun résultat trouvé pour ce livre sur les sources bibliographiques.",
                )
                return

            # 4. Sélection via BnfSelectDialog
            dialog_items = []
            for result in searchresults[:10]:
                dialog_item = {
                    "title": result.display_title,
                    "author": result.authors_display,
                    "year": result.year_display,
                    "publisher": result.publisher or "Éditeur inconnu",
                    "isbn": result.isbn or book.isbn or "",
                    "source": f"[{result.source.name}] Score: {result.score:.1f}/100",
                    "_unified_result": result,
                }
                dialog_items.append(dialog_item)

            from .bnf_select_dialog import BnfSelectDialog

            dialog = BnfSelectDialog(self, items=dialog_items)

            if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_notice:
                selected_result = dialog.selected_notice["_unified_result"]
                self._enrich_book_with_result(book, selected_result)

        except Exception as e:
            QMessageBox.critical(
                self,
                translate("book_list.error_title"),
                translate("book_list.search_error", error=str(e)),
            )

        except Exception as e:
            progress.close()
            QMessageBox.critical(
                self,
                translate("book_list.error_title"),
                translate("book_list.search_error", error=str(e)),
            )
            return

    def _enrich_book_with_result(self, book, result):
        """Enrichit un livre avec les données d'un UnifiedBookResult."""

        # Debug: Afficher les valeurs actuelles
        print("🔍 DEBUG Enrichissement:")
        print("  Livre actuel:")
        print(f"    - title: '{book.title}' (type: {type(book.title)})")
        print(f"    - authors_text: '{book.authors_text}' (type: {type(book.authors_text)})")
        print(f"    - year: '{book.year}' (type: {type(book.year)})")
        print(f"    - isbn: '{book.isbn}' (type: {type(book.isbn)})")
        print(f"    - collection: '{book.collection}' (type: {type(book.collection)})")

        print("  Résultat trouvé:")
        print(f"    - title: '{result.title}' (type: {type(result.title)})")
        print(f"    - authors: {result.authors} (type: {type(result.authors)})")
        print(f"    - year: '{result.year}' (type: {type(result.year)})")
        print(f"    - isbn: '{result.isbn}' (type: {type(result.isbn)})")
        print(f"    - publisher: '{result.publisher}' (type: {type(result.publisher)})")
        print(f"    - collection: '{result.collection}' (type: {type(result.collection)})")

        changes = {}

        # Fonctions helper pour vérifier les valeurs
        def is_empty(value):
            """Vérifie si un champ est vraiment vide."""
            return (
                value is None or value == "None" or (isinstance(value, str) and not value.strip())
            )

        def has_data(value):
            """Vérifie si un champ a des données utiles."""
            return (
                value is not None
                and value != "None"
                and (not isinstance(value, str) or value.strip())
            )

        # 1. ENRICHIR L'ISBN (priorité max)
        if is_empty(book.isbn) and has_data(result.isbn):
            changes["isbn"] = result.isbn
            print(f"    ✅ ISBN à enrichir: '{result.isbn}'")

        # 2. ENRICHIR L'ÉDITEUR (même s'il n'apparaît pas dans la vue)
        try:
            if (
                hasattr(book, "publisher")
                and is_empty(book.publisher)
                and has_data(result.publisher)
            ):
                changes["publisher"] = result.publisher
                print(f"    ✅ Éditeur à enrichir: '{result.publisher}'")
        except AttributeError:
            print("    ⚠️ Le modèle Book n'a pas de champ 'publisher'")

        # 3. AMÉLIORER le titre si celui trouvé est significativement plus précis
        if has_data(result.title) and len(result.title.strip()) > len(book.title.strip()) + 10:
            changes["title"] = result.title
            print(f"    ✅ Titre à enrichir: '{result.title}'")

        # 4. AMÉLIORER les auteurs si plus détaillés
        if is_empty(book.authors_text) and result.authors and len(result.authors) > 0:
            changes["authors_text"] = ", ".join(result.authors)
            print(f"    ✅ Auteurs à enrichir: '{changes['authors_text']}'")

        # 5. NE PAS toucher à la collection interne !
        # Collection interne ('Athéna', 'SEDC') != Collection éditoriale ('Pléiade')
        print(f"    🔒 Collection interne préservée: '{book.collection}'")

        # 6. Année seulement si vraiment absente
        if is_empty(book.year) and has_data(result.year):
            try:
                year_value = int(result.year) if str(result.year).isdigit() else None
                if year_value:
                    changes["year"] = year_value
                    print(f"    ✅ Année à enrichir: '{year_value}'")
            except (ValueError, TypeError):
                print(f"    ⚠️ Année invalide: '{result.year}'")

        # 7. Résumé seulement si vraiment absent  # 🆕 NOUVEAU
        if is_empty(book.summary) and has_data(result.summary):
            changes["summary"] = result.summary
            print(f" ✅ Résumé à enrichir: '{result.summary[:50]}...'")

        print(f"  📋 Changements détectés: {len(changes)}")
        for field, value in changes.items():
            print(f"    - {field}: '{value}'")

        # Afficher un résumé des changements
        if not changes:
            print("    ❌ Aucun changement à appliquer")
            QMessageBox.information(
                self, "Enrichissement", "Aucune nouvelle information à ajouter."
            )
            return

        # Demander confirmation
        changes_text = "\n".join([f"• {field}: {value}" for field, value in changes.items()])
        reply = QMessageBox.question(
            self,
            "Enrichissement",
            f"Appliquer ces améliorations ?\n\n{changes_text}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Appliquer les changements en base
            with get_session() as session:
                book_to_update = session.get(Book, book.id)
                if book_to_update:
                    for field, value in changes.items():
                        setattr(book_to_update, field, value)
                    session.commit()

                    # Rafraîchir l'affichage
                    self.refresh()

                    source_info = f"Source: {result.source.name} (Score: {result.score:.1f}/100)"
                    QMessageBox.information(
                        self, "Enrichissement", f"Livre mis à jour avec succès !\n\n{source_info}"
                    )

    def _on_new_book(self):
        """Ouvre l'éditeur pour créer un nouveau livre."""
        from .book_editor import BookEditor

        dialog = BookEditor(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 🎯 Récupérer le dernier livre créé (par ID max)
            with get_session() as session:
                last_book = session.execute(
                    select(Book).order_by(Book.id.desc()).limit(1)
                ).scalar_one_or_none()

                if last_book:
                    book_id = last_book.id
                    book_title = last_book.title or "(sans titre)"
                    session.expunge(last_book)

            self.refresh()

            # 🎯 AUDIT : Logger la création
            if last_book:
                audit_book_created(book_id=book_id, title=book_title, user="system")

    def _on_export(self) -> None:
        """Exporte la liste des livres (filtrés) vers CSV ou XLSX.

        Ouvre un dialogue permettant de choisir le format, les colonnes,
        et les métadonnées à inclure dans l'export.
        """
        # 1. Préparer les colonnes disponibles (traduites)
        available_columns = {
            col_id: translate(f"book_list.column.{col_id}")
            for col_id in BookTableModel.ALL_COLUMNS.keys()
        }

        # 2. Colonnes actuellement visibles
        visible_columns = self.table_model._visible_columns

        # 3. Colonnes obligatoires (titre et auteur)
        mandatory_columns = ["title", "author"]

        # 4. Ouvrir le dialogue d'export
        dialog = ExportDialog(
            parent=self,
            available_columns=available_columns,
            default_columns=visible_columns,
            mandatory_columns=mandatory_columns,
            preferences=self._prefs,
            export_type="books",
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # 5. Récupérer les choix de l'utilisateur
        selected_format = dialog.get_selected_format()
        selected_columns = dialog.get_selected_columns()
        filepath = dialog.get_filepath()
        metadata_opts = dialog.get_metadata_options()

        if not filepath:
            return

        try:
            # 6. Construire les métadonnées
            metadata = ExportMetadata(
                include_date=metadata_opts["include_date"],
                include_count=metadata_opts["include_count"],
                include_custom_message=metadata_opts["include_custom_message"],
                custom_message=metadata_opts["custom_message"],
                app_name=self._prefs.app_name,
                library_name=self._prefs.library_name if self._prefs.library_name_enabled else "",
            )

            # 7. Préparer les headers (traduits)
            headers = [translate(f"book_list.column.{col_id}") for col_id in selected_columns]

            # 8. Extraire les données des livres FILTRÉS
            filtered_books = self.table_model._filtered_books
            total_books = len(filtered_books)

            # Créer la progress bar
            progress = QProgressDialog(
                translate("export.progress.message"),
                translate("export.progress.cancel"),
                0,
                total_books,
                self,
            )
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(
                500
            )  # N'affiche que si > 500ms (évite flash pour petits exports)

            data_rows = []
            for idx, book in enumerate(filtered_books):
                # Vérifier si l'utilisateur a annulé
                if progress.wasCanceled():
                    return  # Sortie propre sans message

                row = []
                for col_id in selected_columns:
                    # Mapping identique à BookTableModel.data()
                    if col_id == "id":
                        value = str(book.id)
                    elif col_id == "code":
                        value = book.code or ""
                    elif col_id == "title":
                        value = book.title or "(sans titre)"
                    elif col_id == "author":
                        value = book.author or ""
                    elif col_id == "year":
                        value = str(book.year) if book.year else ""
                    elif col_id == "isbn":
                        value = book.isbn or ""
                    elif col_id == "publisher":
                        value = book.publisher or ""
                    elif col_id == "fund":
                        value = book.collection or ""
                    elif col_id == "available":
                        value = f"{book.copies_available}/{book.copies_total}"
                    elif col_id == "summary":
                        value = book.summary or ""
                    elif col_id == "cover_image":
                        value = book.cover_image or ""

                    else:
                        value = ""

                    row.append(value)
                data_rows.append(row)

                # Mettre à jour la progress bar
                progress.setValue(idx + 1)

            progress.close()

            # 9. Nom de la feuille (pour XLSX)
            sheet_name = translate("export.sheet_name.books")

            # 10. Appeler le service d'export
            export_data(
                filepath=filepath,
                headers=headers,
                data=data_rows,
                file_format=selected_format,
                metadata=metadata,
                sheet_name=sheet_name,
            )

            # 🎯 AUDIT : Logger l'export
            from ..services.audit_service import audit_export

            audit_export(count=len(data_rows), format=selected_format, user="system")

            self._prefs.export_last_format = selected_format
            self._prefs.export_last_columns_books = selected_columns
            save_preferences(self._prefs)

            # 11. Confirmer le succès
            QMessageBox.information(
                self,
                translate("export.success_title"),
                translate("export.success_message", count=len(data_rows), path=str(filepath)),
            )

        except Exception as e:
            # 12. Gérer les erreurs
            QMessageBox.critical(
                self,
                translate("export.error_title"),
                translate("export.error_message", error=str(e)),
            )
