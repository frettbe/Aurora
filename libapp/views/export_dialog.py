"""Dialogue de configuration pour l'export de données.

Ce dialogue permet à l'utilisateur de configurer les options d'export :
format de fichier, colonnes à exporter, et métadonnées à inclure.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..services.translation_service import translate

if TYPE_CHECKING:
    from ..services.preferences import Preferences


class ExportDialog(QDialog):
    """Dialogue de configuration pour l'export de données.

    Permet de choisir :
    - Le format d'export (CSV ou XLSX)
    - Les colonnes à exporter
    - Les métadonnées à inclure
    - La destination du fichier
    """

    def __init__(
        self,
        parent: QWidget | None,
        available_columns: dict[str, str],
        default_columns: list[str],
        mandatory_columns: list[str] | None = None,
        preferences: Preferences | None = None,
        export_type: str = "books",
    ):
        """Initialise le dialogue d'export.

        Args:
            parent: Widget parent.
            available_columns: Dict {id_colonne: label_colonne} de toutes les colonnes disponibles.
            default_columns: Liste des IDs de colonnes à cocher par défaut.
            mandatory_columns: Liste des IDs de colonnes obligatoires (non décochables).
            preferences: Objet Preferences pour lire les options métadonnées.
            export_type: Type d'export ("books" ou "members") pour le nom de fichier par défaut.
        """
        super().__init__(parent)

        self._available_columns = available_columns
        self._default_columns = default_columns
        self._mandatory_columns = mandatory_columns or []
        self._prefs = preferences
        self._export_type = export_type

        if preferences and export_type == "books" and preferences.export_last_columns_books:
            self._default_columns = preferences.export_last_columns_books
        elif preferences and export_type == "members" and preferences.export_last_columns_members:
            self._default_columns = preferences.export_last_columns_members
        else:
            self._default_columns = default_columns

        # Widgets à référencer plus tard
        self._column_checkboxes: dict[str, QCheckBox] = {}
        self._format_csv: QRadioButton | None = None
        self._format_xlsx: QRadioButton | None = None
        self._filepath: Path | None = None

        self._setup_ui()
        self._load_preferences()

    def _setup_ui(self) -> None:
        """Configure l'interface utilisateur du dialogue."""
        self.setWindowTitle(translate("export.dialog.title"))
        self.setMinimumWidth(500)

        main_layout = QVBoxLayout(self)

        # Section : Format de fichier
        main_layout.addWidget(self._create_format_section())

        # Section : Colonnes à exporter
        main_layout.addWidget(self._create_columns_section())

        # Section : Métadonnées
        if self._prefs:
            main_layout.addWidget(self._create_metadata_section())

        # Boutons OK / Annuler
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def _create_format_section(self) -> QGroupBox:
        """Crée la section de choix du format d'export.

        Returns:
            QGroupBox contenant les radio buttons CSV/XLSX.
        """
        group = QGroupBox(translate("export.dialog.format_section"))
        layout = QHBoxLayout()

        self._format_csv = QRadioButton("CSV")
        self._format_xlsx = QRadioButton("XLSX (Excel)")
        self._format_xlsx.setChecked(True)  # XLSX par défaut

        # Grouper les boutons radio
        format_group = QButtonGroup(self)
        format_group.addButton(self._format_csv)
        format_group.addButton(self._format_xlsx)

        layout.addWidget(self._format_csv)
        layout.addWidget(self._format_xlsx)
        layout.addStretch()

        group.setLayout(layout)
        return group

    def _create_columns_section(self) -> QGroupBox:
        """Crée la section de sélection des colonnes.

        Returns:
            QGroupBox contenant les checkboxes pour chaque colonne.
        """
        group = QGroupBox(translate("export.dialog.columns_section"))

        # Layout principal
        main_layout = QVBoxLayout()

        # Label d'info
        info_label = QLabel(translate("export.dialog.columns_info"))
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)

        # Zone scrollable pour les checkboxes
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(200)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Créer une checkbox par colonne
        for col_id, col_label in self._available_columns.items():
            checkbox = QCheckBox(col_label)

            # Cocher par défaut si dans default_columns
            if col_id in self._default_columns:
                checkbox.setChecked(True)

            # Désactiver si obligatoire
            if col_id in self._mandatory_columns:
                checkbox.setChecked(True)
                checkbox.setEnabled(False)
                checkbox.setToolTip(translate("export.dialog.column_mandatory"))

            self._column_checkboxes[col_id] = checkbox
            scroll_layout.addWidget(checkbox)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        group.setLayout(main_layout)
        return group

    def _create_metadata_section(self) -> QGroupBox:
        """Crée la section de configuration des métadonnées.

        Returns:
            QGroupBox contenant les options de métadonnées.
        """
        group = QGroupBox(translate("export.dialog.metadata_section"))
        layout = QVBoxLayout()

        # Note : Les checkboxes de métadonnées sont disabled selon les prefs
        # mais on les affiche quand même pour info

        self._meta_date_cb = QCheckBox(translate("export.dialog.meta_date"))
        self._meta_date_cb.setChecked(self._prefs.export_include_date)

        self._meta_count_cb = QCheckBox(translate("export.dialog.meta_count"))
        self._meta_count_cb.setChecked(self._prefs.export_include_count)

        self._meta_custom_cb = QCheckBox(translate("export.dialog.meta_custom"))
        self._meta_custom_cb.setChecked(self._prefs.export_include_custom_message)
        self._meta_custom_cb.toggled.connect(self._on_custom_message_toggled)

        # Champ de texte pour message personnalisé
        self._meta_custom_input = QLineEdit()
        self._meta_custom_input.setPlaceholderText(
            translate("export.dialog.meta_custom_placeholder")
        )
        self._meta_custom_input.setText(self._prefs.export_last_custom_message)
        self._meta_custom_input.setEnabled(self._prefs.export_include_custom_message)

        layout.addWidget(self._meta_date_cb)
        layout.addWidget(self._meta_count_cb)
        layout.addWidget(self._meta_custom_cb)
        layout.addWidget(self._meta_custom_input)

        group.setLayout(layout)
        return group

    def _load_preferences(self) -> None:
        """Charge les préférences utilisateur (si disponibles)."""
        # Pour l'instant, tout est géré dans _create_metadata_section
        # Cette méthode est un placeholder pour extensions futures
        pass

    def _on_custom_message_toggled(self, checked: bool) -> None:
        """Active/désactive le champ de message personnalisé.

        Args:
            checked: True si la checkbox est cochée.
        """
        self._meta_custom_input.setEnabled(checked)

    def _on_accept(self) -> None:
        """Gère le clic sur OK : demande le chemin de sauvegarde."""
        # Déterminer l'extension par défaut
        if self._format_csv and self._format_csv.isChecked():
            default_ext = "csv"
            file_filter = "CSV Files (*.csv);;All Files (*)"
        else:
            default_ext = "xlsx"
            file_filter = "Excel Files (*.xlsx);;All Files (*)"

        # Nom de fichier par défaut
        default_filename = f"export_{self._export_type}.{default_ext}"

        # Dialogue de sauvegarde
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            translate("export.dialog.save_title"),
            default_filename,
            file_filter,
        )

        if filepath:
            self._filepath = Path(filepath)
            self.accept()
        # Sinon, on reste dans le dialogue

    # === Méthodes publiques pour récupérer les choix de l'utilisateur ===

    def get_selected_format(self) -> str:
        """Retourne le format sélectionné ('csv' ou 'xlsx').

        Returns:
            "csv" ou "xlsx" selon le choix de l'utilisateur.
        """
        if self._format_csv and self._format_csv.isChecked():
            return "csv"
        return "xlsx"

    def get_selected_columns(self) -> list[str]:
        """Retourne la liste des IDs de colonnes sélectionnées.

        Returns:
            Liste des identifiants de colonnes à exporter.
        """
        return [
            col_id for col_id, checkbox in self._column_checkboxes.items() if checkbox.isChecked()
        ]

    def get_filepath(self) -> Path | None:
        """Retourne le chemin du fichier de destination.

        Returns:
            Path du fichier, ou None si annulé.
        """
        return self._filepath

    def get_metadata_options(self) -> dict[str, bool | str]:
        """Retourne les options de métadonnées configurées.

        Returns:
            Dictionnaire contenant les options de métadonnées.
        """
        if not self._prefs:
            return {
                "include_date": True,
                "include_count": True,
                "include_custom_message": False,
                "custom_message": "",
            }

        return {
            "include_date": self._meta_date_cb.isChecked(),
            "include_count": self._meta_count_cb.isChecked(),
            "include_custom_message": self._meta_custom_cb.isChecked(),
            "custom_message": self._meta_custom_input.text(),
        }
