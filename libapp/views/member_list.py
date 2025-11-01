"""
Vue principale affichant la liste des membres de la bibliothèque.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QAbstractTableModel, QByteArray, QModelIndex, Qt, Signal, Slot
from PySide6.QtWidgets import (
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

from ..persistence.database import get_session
from ..persistence.models_sa import Member
from ..services.audit_service import (
    audit_member_created,
    audit_member_deleted,
    audit_member_updated,
)
from ..services.export_service import ExportMetadata, export_data
from ..services.preferences import Preferences
from ..services.translation_service import translate
from .export_dialog import ExportDialog
from .natural_sort_proxy import NaturalSortProxyModel

logger = logging.getLogger(__name__)


class MemberTableModel(QAbstractTableModel):
    """Modèle de données Qt pour la table des membres."""

    COLUMNS = [
        "ID",
        "Numéro de membre",
        "Nom",
        "Prénom",
        "Email",
        "Téléphone",
        "Statut",
        "Actif",
    ]

    def __init__(self):
        super().__init__()
        self._all_members: list[Member] = []
        self._filtered_members: list[Member] = []

    def set_members(self, members: list[Member]):
        self.beginResetModel()
        self._all_members = list(members)
        self._filtered_members = list(members)
        self.endResetModel()

    def apply_filter(self, search_text: str):
        search_term = (search_text or "").strip().lower()
        self.beginResetModel()
        if not search_term:
            self._filtered_members = list(self._all_members)
        else:
            self._filtered_members = [
                m
                for m in self._all_members
                if search_term in (m.first_name or "").lower()
                or search_term in (m.last_name or "").lower()
                or search_term in (m.email or "").lower()
            ]
        self.endResetModel()

    def get_member_by_row(self, row: int) -> Member | None:
        if 0 <= row < len(self._filtered_members):
            return self._filtered_members[row]
        return None

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._filtered_members)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> object | None:
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        member = self._filtered_members[index.row()]
        column_data = {
            0: member.id,
            1: member.member_no,
            2: member.last_name,
            3: member.first_name,
            4: member.email,
            5: member.phone,
            6: translate("member.is_active_status")
            if member.is_active
            else translate("member.is_nonactive_status"),
        }
        return column_data.get(index.column())

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole
    ) -> str | None:
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.COLUMNS[section]
        return None

    def get_member_at(self, row: int) -> Member:
        """Retourne le membre à la ligne donnée."""
        return self._filtered_members[row]


class MemberListView(QWidget):
    """Widget principal pour afficher et interagir avec la liste des membres."""

    memberActivated = Signal(int)
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
        filter_layout.addWidget(QLabel(translate("member_list.search_label")))
        self.search_input = QLineEdit()
        self.search_input.setClearButtonEnabled(True)
        filter_layout.addWidget(self.search_input)
        layout.addLayout(filter_layout)

        self.table_view = QTableView()
        self.table_model = MemberTableModel()
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

    def load_view_state(self):
        """Charge l'état de la vue (filtre, colonnes) depuis les préférences."""
        state = self._prefs.members_view_state or {}
        self.search_input.blockSignals(True)
        self.search_input.setText(state.get("search_text", ""))
        self.search_input.blockSignals(False)

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
        self._prefs.members_view_state = state

    @Slot()
    def refresh(self):
        """Recharge les données depuis la BDD et applique le filtre."""
        with get_session() as session:
            result = session.scalars(
                select(Member).order_by(Member.last_name, Member.first_name)
            ).all()

            # 🔧 FIX CRITIQUE : Détacher les objets AVANT la fermeture de la session
            members = []
            for member in result:
                session.expunge(member)  # Détache l'objet de la session
                members.append(member)

        # Maintenant la session est fermée, mais les objets sont accessibles
        self.table_model.set_members(members)
        self._on_filter_changed()

    @Slot()
    def _on_filter_changed(self):
        self.table_model.apply_filter(self.search_input.text())
        self.save_view_state()

    @Slot(QModelIndex)
    def _on_double_clicked(self, index: QModelIndex):
        if not index.isValid():
            return
        source_index = self.proxy_model.mapToSource(index)
        if not source_index.isValid():
            return
        member = self.table_model.get_member_by_row(source_index.row())
        if member:
            self.memberActivated.emit(member.id)

    def contextMenuEvent(self, event):
        """Affiche le menu contextuel pour les actions sur un membre."""
        if not self.table_view.selectionModel().hasSelection():
            return

        # Créer le menu contextuel
        menu = QMenu(self)

        edit_action = menu.addAction(translate("context.edit"))
        edit_action.triggered.connect(self._on_edit)

        history_action = menu.addAction(translate("context.history"))
        history_action.triggered.connect(self._on_history)

        delete_action = menu.addAction(translate("context.delete"))
        delete_action.triggered.connect(self._on_delete)

        menu.addSeparator()  # ← Séparateur visuel

        # 🎯 NOUVELLE ACTION : Export
        export_action = menu.addAction(translate("context.export"))
        export_action.triggered.connect(self._on_export)

        menu.addSeparator()  # ← Séparateur visuel

        new_member_action = menu.addAction(translate("context.new_member"))
        new_member_action.triggered.connect(self._on_new_member)

        # Afficher le menu
        menu.exec(event.globalPos())

    # Ajouter les méthodes stubs :
    def _on_edit(self):
        """Ouvre l'éditeur pour modifier le membre sélectionné."""
        selection = self.table_view.selectionModel().selectedRows()
        if not selection:
            return

        source_index = self.proxy_model.mapToSource(selection[0])
        member = self.table_model._filtered_members[source_index.row()]

        # Sauvegarder l'état avant modification
        old_name = f"{member.last_name} {member.first_name}"

        from .member_editor import MemberEditor

        dialog = MemberEditor(self, member=member)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

            # 🎯 AUDIT : Logger la modification
            new_name = f"{member.last_name} {member.first_name}"
            audit_member_updated(
                member_id=member.id,
                changes={"old_name": old_name, "new_name": new_name},
                user="system",
            )

    def _on_history(self):
        """Afficher l'historique simple du membre."""
        selected_rows = self.table_view.selectionModel().selectedRows()
        if not selected_rows:
            return

        member_index = selected_rows[0].row()
        member = self.table_model.get_member_by_row(member_index)

        if not member:
            return

        # Version simple pour l'instant
        with get_session() as session:
            from ..persistence.models_sa import Loan

            loans = session.scalars(select(Loan).where(Loan.member_id == member.id)).all()

            message = f"Historique de {member.first_name} {member.last_name}:\n"
            message += f"Nombre total de prêts : {len(loans)}\n\n"

            for loan in loans[-5:]:  # 5 derniers
                status = "En cours" if loan.status.value == "open" else "Terminé"
                message += f"• {loan.book.title} - {status}\n"

            QMessageBox.information(self, translate("member_list.loan_history"), message)

    def _on_delete(self):
        """Supprime le membre sélectionné."""
        selection = self.table_view.selectionModel().selectedRows()
        if not selection:
            return

        source_index = self.proxy_model.mapToSource(selection[0])
        member = self.table_model._filtered_members[source_index.row()]

        # Sauvegarder les infos avant suppression
        member_id = member.id
        member_name = f"{member.last_name} {member.first_name}"

        # Dialogue de confirmation
        reply = QMessageBox.question(
            self,
            translate("member_list.delete_title"),
            translate("member_list.delete_confirm", name=member_name),
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            try:
                with get_session() as session:
                    member_to_delete = session.get(Member, member_id)
                    if member_to_delete:
                        session.delete(member_to_delete)
                        session.commit()

                self.refresh()

                # 🎯 AUDIT : Logger la suppression
                audit_member_deleted(member_id=member_id, name=member_name, user="system")

                QMessageBox.information(
                    self,
                    translate("member_list.delete_success_title"),
                    translate("member_list.delete_success_body"),
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    translate("errors.delete_member_title"),
                    translate("errors.delete_member_body", error=str(e)),
                )

    def _on_new_member(self):
        """Ouvre l'éditeur pour créer un nouveau membre."""
        from .member_editor import MemberEditor

        dialog = MemberEditor(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 🎯 Récupérer le dernier membre créé
            with get_session() as session:
                last_member = session.execute(
                    select(Member).order_by(Member.id.desc()).limit(1)
                ).scalar_one_or_none()

                if last_member:
                    member_id = last_member.id
                    member_name = f"{last_member.last_name} {last_member.first_name}"
                    session.expunge(last_member)

            self.refresh()

            # 🎯 AUDIT : Logger la création
            if last_member:
                audit_member_created(member_id=member_id, name=member_name, user="system")

    def _on_export(self) -> None:
        """Exporte la liste des membres (filtrés) vers CSV ou XLSX.

        Ouvre un dialogue permettant de choisir le format, les colonnes,
        et les métadonnées à inclure dans l'export.
        """
        # 1. Définir les colonnes disponibles avec mapping
        # Basé sur MemberTableModel.COLUMNS
        column_mapping = {
            "id": "ID",
            "member_no": "Numéro de membre",
            "last_name": "Nom",
            "first_name": "Prénom",
            "email": "Email",
            "phone": "Téléphone",
            "status": "Statut",
            "is_active": "Actif",
        }

        # 2. Colonnes à afficher par défaut (toutes)
        default_columns = list(column_mapping.keys())

        # 3. Colonnes obligatoires (nom et prénom)
        mandatory_columns = ["last_name", "first_name"]

        # 4. Ouvrir le dialogue d'export
        dialog = ExportDialog(
            parent=self,
            available_columns=column_mapping,
            default_columns=default_columns,
            mandatory_columns=mandatory_columns,
            preferences=self._prefs,
            export_type="members",
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
            headers = [column_mapping[col_id] for col_id in selected_columns]

            # 8. Extraire les données des membres FILTRÉS
            data_rows = []
            for member in self.table_model._filtered_members:
                row = []
                for col_id in selected_columns:
                    value = self._get_member_column_value(member, col_id)
                    row.append(value)
                data_rows.append(row)

            # 9. Nom de la feuille (pour XLSX)
            sheet_name = translate("export.sheet_name.members")

            # 10. Appeler le service d'export
            export_data(
                filepath=filepath,
                headers=headers,
                data=data_rows,
                file_format=selected_format,
                metadata=metadata,
                sheet_name=sheet_name,
            )

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

    def _get_member_column_value(self, member: Member, col_id: str) -> str:
        """Extrait la valeur d'une colonne pour un membre donné.

        Args:
            member: L'objet Member.
            col_id: L'identifiant de la colonne.

        Returns:
            La valeur formatée pour l'export.
        """
        if col_id == "id":
            return str(member.id)
        elif col_id == "lmember_no":
            return member.member_no or ""
        elif col_id == "last_name":
            return member.last_name or ""
        elif col_id == "first_name":
            return member.first_name or ""
        elif col_id == "email":
            return member.email or ""
        elif col_id == "phone":
            return member.phone or ""
        elif col_id == "is_active":
            return (
                translate("member.is_active_status")
                if member.is_active
                else translate("member.is_nonactive_status")
            )
        else:
            return ""
