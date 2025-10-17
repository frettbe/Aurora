"""
Vue principale pour l'affichage et la gestion de la liste des prêts.

Ce module définit une architecture complète pour afficher les prêts :
- LoanRow: Un dataclass simple pour représenter les données d'une ligne de tableau.
- LoanTableModel: Le modèle de données Qt qui gère le tri, le filtrage et
  le style conditionnel (ex: couleur pour les retards).
- LoanListView: Le widget principal qui assemble la barre de filtres et le
  tableau, et gère toutes les interactions utilisateur.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QAbstractTableModel,
    QByteArray,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
    Signal,
    Slot,
)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QTableView,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from ..persistence.database import get_session
from ..persistence.models_sa import Loan, LoanStatus
from ..services.export_service import ExportMetadata, export_data
from ..services.loan_service import is_overdue
from ..services.preferences import Preferences, save_preferences
from ..services.translation_service import translate
from .export_dialog import ExportDialog
from .loan_dialogs import ReturnLoanDialog


class LoanTableModel(QAbstractTableModel):
    """Modèle de données Qt pour la table des prêts."""

    COLUMNS = ["ID", "Livre", "Membre", "Date d'emprunt", "Date d'échéance", "Statut"]

    def __init__(self):
        super().__init__()
        self._all_loans: list[Loan] = []
        self._filtered_loans: list[Loan] = []

    def get_loan_by_row(self, row: int) -> Loan | None:
        """Retourne le prêt à la ligne donnée."""
        if 0 <= row < len(self._filtered_loans):
            return self._filtered_loans[row]
        return None

    def set_loans(self, loans: list[Loan]):
        self.beginResetModel()
        self._all_loans = list(loans)
        self._filtered_loans = list(loans)
        self.endResetModel()

    def apply_filters(self, status: str, overdue_only: bool, search_text: str):
        search_term = (search_text or "").strip().lower()
        self.beginResetModel()
        filtered = self._all_loans
        if status != "Tous":
            try:
                loan_status = LoanStatus(status)
                filtered = [loan for loan in filtered if loan.status == loan_status]
            except ValueError:
                pass
        if overdue_only:
            filtered = [loan for loan in filtered if is_overdue(loan.due_date, loan.return_date)]
        if search_term:
            filtered = [
                loan
                for loan in filtered
                if search_term in (loan.book.title or "").lower()
                or search_term
                in f"{loan.member.first_name or ''} {loan.member.last_name or ''}".lower()
            ]
        self._filtered_loans = filtered
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._filtered_loans)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> object | None:
        if not index.isValid():
            return None
        loan = self._filtered_loans[index.row()]
        if role == Qt.ItemDataRole.ForegroundRole and is_overdue(loan.due_date, loan.return_date):
            return QColor("red")
        if role == Qt.ItemDataRole.DisplayRole:
            column_data = {
                0: loan.id,
                1: loan.book.title if loan.book else "N/A",
                2: f"{loan.member.first_name or ''} {loan.member.last_name or ''}".strip()
                if loan.member
                else "N/A",
                3: loan.loan_date.isoformat() if loan.loan_date else "",
                4: loan.due_date.isoformat() if loan.due_date else "",
                5: loan.status.value if loan.status else "",
            }
            return column_data.get(index.column())
        return None

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole
    ) -> str | None:
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.COLUMNS[section]
        return None


class LoanListView(QWidget):
    """Widget principal pour afficher et interagir avec la liste des prêts."""

    # Le signal que app.py essaie de connecter
    loanActivated = Signal(int)

    def __init__(self, parent: QWidget, prefs: Preferences):
        super().__init__(parent)
        self._prefs = prefs
        self._setup_ui()
        self._connect_signals()
        self._load_view_state()
        self.refresh()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        filters_layout = QHBoxLayout()
        filters_layout.addWidget(QLabel(translate("loan_list.status_label")))
        self.status_combo = QComboBox()
        self.status_combo.addItem(translate("loan_list.all_status"))
        self.status_combo.addItems([s.value for s in LoanStatus])
        filters_layout.addWidget(self.status_combo)
        self.overdue_checkbox = QCheckBox()  # ← CRÉER D'ABORD
        self.overdue_checkbox.setText(translate("loan_list.overdue_only_checkbox"))
        filters_layout.addWidget(self.overdue_checkbox)
        filters_layout.addStretch()
        filters_layout.addWidget(QLabel(translate("loan_list.search_label")))
        self.search_input = QLineEdit()
        self.search_input.setClearButtonEnabled(True)
        filters_layout.addWidget(self.search_input)
        main_layout.addLayout(filters_layout)

        self.table_view = QTableView()
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table_model = LoanTableModel()
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.table_model)
        self.table_view.setModel(self.proxy_model)
        self.table_view.setSortingEnabled(True)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        main_layout.addWidget(self.table_view)

    def _connect_signals(self):
        self.status_combo.currentTextChanged.connect(self._on_filters_changed)
        self.overdue_checkbox.stateChanged.connect(self._on_filters_changed)
        self.search_input.textChanged.connect(self._on_filters_changed)
        # On connecte le double-clic pour qu'il émette le signal
        self.table_view.doubleClicked.connect(self._on_double_clicked)

    def _load_view_state(self):
        state = self._prefs.loans_view_state or {}
        self.status_combo.blockSignals(True)
        self.overdue_checkbox.blockSignals(True)
        self.search_input.blockSignals(True)
        self.status_combo.setCurrentText(state.get("status_filter", "Tous"))
        self.overdue_checkbox.setChecked(state.get("overdue_only", False))
        self.search_input.setText(state.get("search_text", ""))
        self.status_combo.blockSignals(False)
        self.overdue_checkbox.blockSignals(False)
        self.search_input.blockSignals(False)
        if header_state := state.get("header_state"):
            self.table_view.horizontalHeader().restoreState(
                QByteArray.fromBase64(header_state.encode("ascii"))
            )

    def save_view_state(self):
        state = {
            "status_filter": self.status_combo.currentText(),
            "overdue_only": self.overdue_checkbox.isChecked(),
            "search_text": self.search_input.text(),
            "header_state": self.table_view.horizontalHeader()
            .saveState()
            .toBase64()
            .data()
            .decode("ascii"),
        }
        self._prefs.loans_view_state = state
        save_preferences(self._prefs)

    def get_selected_loan_id(self) -> int | None:
        sel = self.table_view.selectionModel()
        if not sel or not sel.hasSelection():
            return None
        proxy_index = sel.selectedRows()[0]  # index dans le PROXY
        source_index = self.proxy_model.mapToSource(proxy_index)  # map → SOURCE
        if not source_index.isValid():
            return None
        loan = self.table_model.get_loan_by_row(source_index.row())
        return loan.id if loan else None

    @Slot(QModelIndex)
    def _on_double_clicked(self, index: QModelIndex):
        """Au double-clic, ouvre ReturnLoanDialog pour ce prêt."""
        if not index.isValid():
            return
        source_index = self.proxy_model.mapToSource(index)
        if not source_index.isValid():
            return
        loan = self.table_model.get_loan_by_row(source_index.row())
        if loan and loan.status == LoanStatus.open:
            dialog = ReturnLoanDialog(self, preselected_loan_id=loan.id)
            if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_loan_id:
                from ..services.loan_service import return_loan as service_return

                service_return(dialog.selected_loan_id)
                self.refresh()

    @Slot()
    def refresh(self):
        with get_session() as s:
            loans = s.scalars(
                select(Loan)
                .options(joinedload(Loan.book), joinedload(Loan.member))
                .order_by(Loan.loan_date.desc())
            ).all()
            self.table_model.set_loans(loans)
        self._on_filters_changed()

    @Slot()
    def _on_filters_changed(self):
        self.table_model.apply_filters(
            status=self.status_combo.currentText(),
            overdue_only=self.overdue_checkbox.isChecked(),
            search_text=self.search_input.text(),
        )
        self.save_view_state()

    def contextMenuEvent(self, event):
        # 1) Trouver l'index (PROXY) sous le curseur
        vp_pos = self.table_view.viewport().mapFrom(self, event.pos())
        proxy_index = self.table_view.indexAt(vp_pos)

        sel_model = self.table_view.selectionModel()

        if proxy_index.isValid():
            # 2) Sélectionner visuellement cette ligne (UX attendue d’un clic droit)
            self.table_view.selectRow(proxy_index.row())
            self._stored_proxy_index = proxy_index
        else:
            # 3) Sinon, retomber sur la sélection courante si elle existe
            rows = sel_model.selectedRows()
            if not rows:
                return
            self._stored_proxy_index = rows[0]

        # (debug) voir le mapping proxy → source
        src = self.proxy_model.mapToSource(self._stored_proxy_index)
        print(
            f"[ctx] proxy_row={self._stored_proxy_index.row()} -> source_row={src.row()}",
            flush=True,
        )

        menu = QMenu(self)
        return_action = menu.addAction(translate("loan_list.context_return_book"))
        return_action.triggered.connect(self._on_return_loan)
        menu.addSeparator()  # 🔥 Séparateur

        # 🔥 Nouvelle action : Export
        export_action = menu.addAction(translate("context.export"))
        export_action.triggered.connect(self._on_export)
        menu.exec(event.globalPos())

    def _on_return_loan(self):
        sel_rows = self.table_view.selectionModel().selectedRows()

        if sel_rows:
            proxy_index = sel_rows[0]
        elif hasattr(self, "_stored_proxy_index") and self._stored_proxy_index.isValid():
            proxy_index = self._stored_proxy_index
        else:
            return

        source_index = self.proxy_model.mapToSource(proxy_index)
        if not source_index.isValid():
            return

        loan = self.table_model.get_loan_by_row(source_index.row())
        if not loan or loan.status != LoanStatus.open:
            QMessageBox.warning(
                self,
                translate("loan_list.return_error_title"),
                translate("loan_list.return_error_message"),
            )
            return

        print(
            f"[return] id={loan.id} (proxy_row={proxy_index.row()} -> source_row={source_index.row()})",
            flush=True,
        )

        dialog = ReturnLoanDialog(self, preselected_loan_id=loan.id)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_loan_id:
            from ..services.loan_service import return_loan as service_return_loan

            print(f"[return] dialog.selected_loan_id={dialog.selected_loan_id}", flush=True)
            service_return_loan(dialog.selected_loan_id)
            self.refresh()

    @Slot()
    def filter_overdue(self):
        """Filtre la liste pour afficher seulement les prêts en retard."""
        self.overdue_checkbox.setChecked(True)
        # 🔥 Appeler la méthode correcte qui existe déjà
        self._on_filters_changed()

    def _on_export(self) -> None:
        """Exporte la liste des prêts (filtrés) vers CSV ou XLSX."""

        # 1. Définir les colonnes disponibles
        column_mapping = {
            "id": "ID",
            "book_title": "Livre",
            "member_name": "Membre",
            "loan_date": "Date d'emprunt",
            "due_date": "Date d'échéance",
            "return_date": "Date de retour",
            "status": "Statut",
        }

        # 2. Colonnes par défaut (toutes)
        default_columns = list(column_mapping.keys())

        # 3. Colonnes obligatoires
        mandatory_columns = ["book_title", "member_name", "loan_date"]

        # 4. Ouvrir le dialogue
        dialog = ExportDialog(
            parent=self,
            available_columns=column_mapping,
            default_columns=default_columns,
            mandatory_columns=mandatory_columns,
            preferences=self._prefs,
            export_type="loans",
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # 5. Récupérer les choix
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

            # 7. Headers traduits
            headers = [column_mapping[col_id] for col_id in selected_columns]

            # 8. Extraire les données des prêts FILTRÉS
            data_rows = []
            for loan in self.table_model._filtered_loans:
                row = []
                for col_id in selected_columns:
                    value = self._get_loan_column_value(loan, col_id)
                    row.append(value)
                data_rows.append(row)

            # 9. Nom de feuille
            sheet_name = translate("export.sheet_name.loans")

            # 10. Exporter
            export_data(
                filepath=filepath,
                headers=headers,
                data=data_rows,
                file_format=selected_format,
                metadata=metadata,
                sheet_name=sheet_name,
            )

            # 11. Succès
            QMessageBox.information(
                self,
                translate("export.success_title"),
                translate("export.success_message", count=len(data_rows), path=str(filepath)),
            )

        except Exception as e:
            # 12. Erreur
            QMessageBox.critical(
                self,
                translate("export.error_title"),
                translate("export.error_message", error=str(e)),
            )

    def _get_loan_column_value(self, loan: Loan, col_id: str) -> str:
        """Extrait la valeur d'une colonne pour un prêt donné."""
        if col_id == "id":
            return str(loan.id)
        elif col_id == "book_title":
            return loan.book.title if loan.book else "N/A"
        elif col_id == "member_name":
            if loan.member:
                return f"{loan.member.first_name or ''} {loan.member.last_name or ''}".strip()
            return "N/A"
        elif col_id == "loan_date":
            return loan.loan_date.isoformat() if loan.loan_date else ""
        elif col_id == "due_date":
            return loan.due_date.isoformat() if loan.due_date else ""
        elif col_id == "return_date":
            return loan.return_date.isoformat() if loan.return_date else ""
        elif col_id == "status":
            return loan.status.value if loan.status else ""
        else:
            return ""
