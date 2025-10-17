"""
Fenêtre de dialogue pour l'importation de données depuis un fichier.

Ce module gère le processus d'importation de livres à partir de
fichiers CSV ou Excel, en guidant l'utilisateur à travers les étapes
de sélection de fichier, de mappage de colonnes et de validation.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
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

from ..services.import_service import parse_xlsx, upsert_rows, validate_rows
from ..services.preferences import Preferences, save_preferences
from ..services.translation_service import translate
from ..services.types import ImportErrorItem

BOOK_FIELDS = [
    "title",
    "author",
    "volume",
    "year",
    "code",
    "fund",
    "isbn",
    "publisher",
    "copies_total",
    "copies_available",
]


def t(key: str, default: str) -> str:
    """Fallback de traduction: retourne default si translate renvoie la clé."""
    val = translate(key)
    return val if val and val != key else default


class ImportDialog(QDialog):
    """Assistant d'importation de livres."""

    def __init__(self, parent: QWidget, prefs: Preferences):
        super().__init__(parent)
        self.setWindowTitle(translate("import_dialog.title"))
        self.setMinimumWidth(760)
        self._prefs = prefs
        self.file_path: Path | None = None
        self.file_headers: list[str] = []
        self.mapping_combos: dict[str, QComboBox] = {}
        self.report_data: list[ImportErrorItem] = []
        self._setup_ui()
        self._connect_signals()
        self._load_prefs()

    def _setup_ui(self):
        v = QVBoxLayout(self)
        self._create_file_selection_ui(v)
        self._create_mapping_ui(v)
        self._create_options_ui(v)
        self._create_progress_ui(v)
        self._create_report_ui(v)
        self._create_actions(v)

    def _create_file_selection_ui(self, layout: QVBoxLayout):
        hl = QHBoxLayout()
        self.file_label = QLabel(translate("import_dialog.no_file_label"))
        self.pick_file_btn = QPushButton(translate("import_dialog.browse_button"))
        hl.addWidget(self.file_label)
        hl.addStretch()
        hl.addWidget(self.pick_file_btn)
        layout.addLayout(hl)

    def _create_mapping_ui(self, layout: QVBoxLayout):
        form = QFormLayout()
        form.setContentsMargins(0, 12, 0, 12)
        for field in BOOK_FIELDS:
            cb = QComboBox()
            self.mapping_combos[field] = cb
            field_label = translate(f"book_editor.{field}", default=field.replace("_", " ").title())
            form.addRow(f"{field_label} →", cb)
        layout.addLayout(form)

    def _create_options_ui(self, layout: QVBoxLayout):
        # Groupe options d'import
        grid = QGridLayout()
        options_label = QLabel(translate("import_dialog.options_label"))
        grid.addWidget(QLabel(translate("import_dialog.policy_label")), 0, 0, Qt.AlignRight)
        layout.addWidget(options_label)

        # Politique de mise à jour
        self.policy_combo = QComboBox()
        self.policy_combo.addItems(
            [
                translate("import_dialog.policy_merge"),
                translate("import_dialog.policy_skip"),
                translate("import_dialog.policy_replace"),
            ]
        )
        grid.addWidget(QLabel(translate("import_dialog.policy_label")), 0, 0, Qt.AlignRight)
        grid.addWidget(self.policy_combo, 0, 1)

        layout.addLayout(grid)

        # Options d'enrichissement
        self.chk_bnf = QCheckBox()
        self.chk_bnf_fallback = QCheckBox()
        self.chk_openlibrary = QCheckBox()
        enrichment_label = QLabel("Enrichissement automatique")
        enrichment_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(enrichment_label)

        self.chk_bnf.setText(translate("import_dialog.enrichment_label"))
        self.chk_bnf.setChecked(False)
        layout.addWidget(self.chk_bnf)

        self.chk_bnf_fallback.setText(translate("import_dialog.chk_bnf_fallback"))
        self.chk_bnf_fallback.setChecked(False)
        self.chk_bnf_fallback.setEnabled(False)
        layout.addWidget(self.chk_bnf_fallback)

        self.chk_openlibrary.setText(translate("import_dialog.chk_openlibrary"))
        self.chk_openlibrary.setChecked(False)
        self.chk_openlibrary.setEnabled(False)
        layout.addWidget(self.chk_openlibrary)
        next_row = 1
        for cb in (self.chk_bnf, self.chk_bnf_fallback, self.chk_openlibrary):
            grid.addWidget(cb, next_row, 1)
            next_row += 1
        # Logique d'activation/désactivation
        self.chk_bnf.toggled.connect(self._on_bnf_toggled)
        self.chk_bnf.stateChanged.connect(self._on_bnf_toggled)

    def _on_bnf_toggled(self, checked: bool):
        """Active/désactive les options liées à BnF."""
        self.chk_bnf_fallback.setEnabled(checked)
        self.chk_openlibrary.setEnabled(checked)

    def _create_progress_ui(self, layout: QVBoxLayout):
        self.progress = QProgressBar()
        self.progress_label = QLabel("")
        self.progress.setVisible(False)
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress)
        layout.addWidget(self.progress_label)

    def _create_report_ui(self, layout: QVBoxLayout):
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
        layout.addWidget(self.report_table)
        self.export_btn = QPushButton()
        self.export_btn.setText(translate("import_dialog.export_report_button"))
        self.export_btn.setVisible(False)
        layout.addWidget(self.export_btn)

    def _create_actions(self, layout: QVBoxLayout):
        hl = QHBoxLayout()
        self.import_btn = QPushButton()
        self.import_btn.setText(translate("import_dialog.import_button"))
        self.import_btn.setEnabled(False)
        cancel_btn = QPushButton(translate("buttons.cancel"))
        cancel_btn.setText(translate("buttons.cancel"))
        hl.addStretch()
        hl.addWidget(self.import_btn)
        hl.addWidget(cancel_btn)
        layout.addLayout(hl)
        cancel_btn.clicked.connect(self.reject)

    def _connect_signals(self):
        self.pick_file_btn.clicked.connect(self._on_pick_file)
        self.import_btn.clicked.connect(self._on_import)
        self.export_btn.clicked.connect(self._on_export_report)

    def _load_prefs(self):
        # restaurer dernière policy si existante
        policy = getattr(self._prefs, "import_policy", None)
        if policy:
            self.policy_combo.setCurrentText(str(policy))

    @Slot()
    def _on_pick_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            translate("import_dialog.file_dialog_title"),
            "",
            "Excel & CSV (*.xlsx *.xls *.csv)",
        )
        if not path:
            return
        self.file_path = Path(path)
        self.file_label.setText(self.file_path.name)
        try:
            # lecture headers (xlsx préféré; pandas gère aussi csv)
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
                translate("import_dialog.error_read_headers_message", error=str(e)),
            )
            self.import_btn.setEnabled(False)
            return
        self._populate_mapping_combos()
        self._restore_last_mapping()
        self._apply_auto_suggestions()
        self.import_btn.setEnabled(True)

    def _apply_auto_suggestions(self):
        """Essaie de mapper automatiquement les colonnes avec algorithme intelligent + historique."""

        # Étape 1: Essaie d'abord le mapping historique (fiable)
        last_mapping = self._prefs.import_last_mapping or {}
        applied_from_history = set()

        for field, combo in self.mapping_combos.items():
            if wanted_column := last_mapping.get(field):
                index = combo.findText(wanted_column, Qt.MatchFlag.MatchFixedString)
                if index >= 0:
                    combo.setCurrentIndex(index)
                    applied_from_history.add(field)

        # Étape 2: Pour les champs non mappés, utilise l'algorithme intelligent
        unmapped_fields = [field for field in BOOK_FIELDS if field not in applied_from_history]

        if unmapped_fields and hasattr(self, "file_headers"):
            from ..services.column_mapping import suggest_column_mapping

            suggestions = suggest_column_mapping(self.file_headers, unmapped_fields)

            for field, suggested_column in suggestions.items():
                if field in self.mapping_combos:
                    combo = self.mapping_combos[field]
                    index = combo.findText(suggested_column, Qt.MatchFlag.MatchFixedString)
                    if index >= 0:
                        combo.setCurrentIndex(index)

    def _populate_mapping_combos(self):
        for cb in self.mapping_combos.values():
            cb.clear()
            cb.addItem("(ignorer)", "")
            for h in self.file_headers:
                cb.addItem(h, h)

    def _restore_last_mapping(self):
        last = getattr(self._prefs, "import_last_mapping", {}) or {}
        for field, cb in self.mapping_combos.items():
            wanted = last.get(field)
            if not wanted:
                continue
            idx = cb.findText(wanted, Qt.MatchFlag.MatchFixedString)
            if idx >= 0:
                cb.setCurrentIndex(idx)

    @Slot()
    def _on_import(self):
        if not self.file_path:
            QMessageBox.warning(
                self,
                translate("import_dialog.error_no_file_title"),
                translate("import_dialog.error_no_file_message"),
            )
            return
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

        # persist prefs
        self._prefs.import_policy = self.policy_combo.currentText()
        self._prefs.import_last_mapping = {
            f: cb.currentText() for f, cb in self.mapping_combos.items()
        }
        save_preferences(self._prefs)

        # pipeline
        self.progress.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress.setMaximum(0)  # indéterminé pendant parse
        self.progress_label.setText(translate("import_dialog.progress.reading"))
        batch = parse_xlsx(str(self.file_path), user_mapping)
        self._handle_messages(batch.errors)

        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress_label.setText(translate("import_dialog.progress.validation"))
        rows, warns = validate_rows(batch.rows)
        self._handle_messages(warns)

        self.progress_label.setText(translate("import_dialog.progress.saving"))
        result = upsert_rows(rows, on_isbn_conflict=self.policy_combo.currentText())
        self._handle_messages(result.errors)

        self.progress.setVisible(False)
        self.progress_label.setVisible(False)
        ok = result.inserted + result.updated
        QMessageBox.information(
            self,
            translate("import_dialog.import_done_title"),
            f"{ok} {translate('import_dialog.import_done_message')}",
        )
        self.accept()

    def _handle_messages(self, items: list[ImportErrorItem]):
        if not items:
            return
        # remplir le tableau
        old = self.report_table.rowCount()
        self.report_table.setRowCount(old + len(items))
        for i, m in enumerate(items, start=old):
            self.report_table.setItem(i, 0, QTableWidgetItem(str(getattr(m, "row_index", ""))))
            self.report_table.setItem(i, 1, QTableWidgetItem(str(getattr(m, "field", ""))))
            self.report_table.setItem(i, 2, QTableWidgetItem(str(getattr(m, "severity", "info"))))
            self.report_table.setItem(i, 3, QTableWidgetItem(str(getattr(m, "message", ""))))
        self.report_table.setVisible(True)
        self.export_btn.setVisible(True)

    @Slot()
    def _on_export_report(self):
        if self.report_table.rowCount() == 0:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter le rapport", "import_report.csv", "CSV (*.csv)"
        )
        if not path:
            return
        # extraction simple depuis le tableau
        rows = []
        for i in range(self.report_table.rowCount()):
            rows.append(
                {
                    "row_index": self.report_table.item(i, 0).text(),
                    "field": self.report_table.item(i, 1).text(),
                    "severity": self.report_table.item(i, 2).text(),
                    "message": self.report_table.item(i, 3).text(),
                }
            )
        # écriture CSV
        import csv

        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["row_index", "field", "severity", "message"])
            w.writeheader()
            w.writerows(rows)
