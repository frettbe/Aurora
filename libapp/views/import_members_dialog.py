"""
Dialogue d'importation de membres depuis fichier XLSX/CSV.

Version simplifiée inspirée de import_dialog.py pour les livres.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..services.import_service import parse_members_xlsx, upsert_members
from ..services.preferences import Preferences
from ..services.translation_service import translate
from ..services.types import ImportErrorItem

# Champs membres à mapper
MEMBER_FIELDS = [
    "member_no",
    "first_name",
    "last_name",
    "email",
    "phone",
    "status",
    "is_active",
]


class ImportMembersDialog(QDialog):
    """Assistant d'importation de membres."""

    def __init__(self, parent: QWidget, prefs: Preferences):
        super().__init__(parent)
        self.setWindowTitle(translate("import_members_dialog.title"))
        self.setMinimumWidth(700)
        self._prefs = prefs
        self.file_path: Path | None = None
        self.file_headers: list[str] = []
        self.mapping_combos: dict[str, QComboBox] = {}
        self.report_data: list[ImportErrorItem] = []

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Construit l'interface."""
        v = QVBoxLayout(self)

        # Sélection fichier
        hl = QHBoxLayout()
        self.file_label = QLabel(translate("import_dialog.no_file_label"))
        self.pick_file_btn = QPushButton(translate("import_dialog.browse_button"))
        hl.addWidget(self.file_label)
        hl.addStretch()
        hl.addWidget(self.pick_file_btn)
        v.addLayout(hl)

        # Mapping des colonnes
        form = QFormLayout()
        form.setContentsMargins(0, 12, 0, 12)

        for field in MEMBER_FIELDS:
            cb = QComboBox()
            self.mapping_combos[field] = cb
            field_label = translate(f"member.{field}", default=field.replace("_", " ").title())
            form.addRow(f"{field_label} →", cb)

        v.addLayout(form)

        # Politique de conflit
        policy_layout = QHBoxLayout()
        policy_layout.addWidget(QLabel(translate("import_members_dialog.policy_label")))
        self.policy_combo = QComboBox()
        self.policy_combo.addItems(
            [
                translate("import_members_dialog.policy_skip"),
                translate("import_members_dialog.policy_update"),
            ]
        )
        policy_layout.addWidget(self.policy_combo)
        policy_layout.addStretch()
        v.addLayout(policy_layout)

        # Barre de progression
        self.progress = QProgressBar()
        self.progress_label = QLabel("")
        self.progress.setVisible(False)
        self.progress_label.setVisible(False)
        v.addWidget(self.progress)
        v.addWidget(self.progress_label)

        # Tableau de rapport
        self.report_table = QTableWidget(0, 4)
        self.report_table.setHorizontalHeaderLabels(
            [
                translate("import_dialog.report_table_headers.line"),
                translate("import_dialog.report_table_headers.field"),
                translate("import_dialog.report_table_headers.severity"),
                translate("import_dialog.report_table_headers.message"),
            ]
        )
        self.report_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.report_table.setVisible(False)
        v.addWidget(self.report_table)

        # Boutons
        btn_layout = QHBoxLayout()
        self.import_btn = QPushButton(translate("import_dialog.import_button"))
        self.import_btn.setEnabled(False)
        cancel_btn = QPushButton(translate("buttons.cancel"))
        btn_layout.addStretch()
        btn_layout.addWidget(self.import_btn)
        btn_layout.addWidget(cancel_btn)
        v.addLayout(btn_layout)

        cancel_btn.clicked.connect(self.reject)

    def _connect_signals(self):
        """Connecte les signaux."""
        self.pick_file_btn.clicked.connect(self._on_pick_file)
        self.import_btn.clicked.connect(self._on_import)

    @Slot()
    def _on_pick_file(self):
        """Ouvre le sélecteur de fichier."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            translate("import_members_dialog.file_dialog_title"),
            "",
            "Excel & CSV (*.xlsx *.xls *.csv)",
        )

        if not path:
            return

        self.file_path = Path(path)
        self.file_label.setText(self.file_path.name)

        try:
            # Lire les headers
            df = (
                pd.read_excel(self.file_path, nrows=0)
                if self.file_path.suffix.lower() in (".xlsx", ".xls")
                else pd.read_csv(self.file_path, nrows=0)
            )
            self.file_headers = list(df.columns)
        except Exception as e:
            QMessageBox.warning(
                self,
                translate("import_dialog.error_read_headers_title"),
                f"Erreur lecture fichier: {e}",
            )
            self.import_btn.setEnabled(False)
            return

        self._populate_mapping_combos()
        self.import_btn.setEnabled(True)

    def _populate_mapping_combos(self):
        """Remplit les combos de mapping."""
        for cb in self.mapping_combos.values():
            cb.clear()
            cb.addItem("(ignorer)", "")
            for h in self.file_headers:
                cb.addItem(h, h)

    @Slot()
    def _on_import(self):
        """Lance l'import."""
        if not self.file_path:
            QMessageBox.warning(
                self,
                translate("import_dialog.error_no_file_title"),
                translate("import_dialog.error_no_file_message"),
            )
            return

        # Récupérer le mapping
        user_mapping = {
            field: cb.currentData() for field, cb in self.mapping_combos.items() if cb.currentData()
        }

        if not user_mapping:
            QMessageBox.warning(
                self,
                translate("import_dialog.error_no_mapping_title"),
                translate("import_dialog.error_no_mapping_message"),
            )
            return

        # Parsing
        self.progress.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress.setMaximum(0)
        self.progress_label.setText(translate("import_dialog.progress.reading"))

        batch = parse_members_xlsx(str(self.file_path), user_mapping)
        self._handle_messages(batch.errors)

        # Import
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress_label.setText(translate("import_dialog.progress.saving"))

        policy_text = self.policy_combo.currentText()
        policy = (
            "update"
            if "Mettre à jour" in policy_text or "update" in policy_text.lower()
            else "skip"
        )

        result = upsert_members(batch.rows, on_conflict=policy)
        self._handle_messages(result.errors)

        self.progress.setVisible(False)
        self.progress_label.setVisible(False)

        # Message de succès
        ok = result.inserted + result.updated
        QMessageBox.information(
            self,
            translate("import_dialog.import_done_title"),
            f"{ok} membre(s) importé(s) avec succès !\n"
            f"Insérés: {result.inserted}, Mis à jour: {result.updated}, Ignorés: {result.skipped}",
        )

        self.accept()

    def _handle_messages(self, items: list[ImportErrorItem]):
        """Affiche les erreurs dans le tableau."""
        if not items:
            return

        old = self.report_table.rowCount()
        self.report_table.setRowCount(old + len(items))

        for i, m in enumerate(items, start=old):
            self.report_table.setItem(i, 0, QTableWidgetItem(str(getattr(m, "row_index", ""))))
            self.report_table.setItem(i, 1, QTableWidgetItem(str(getattr(m, "field", ""))))
            self.report_table.setItem(i, 2, QTableWidgetItem(str(getattr(m, "severity", "info"))))
            self.report_table.setItem(i, 3, QTableWidgetItem(str(getattr(m, "message", ""))))

        self.report_table.setVisible(True)
