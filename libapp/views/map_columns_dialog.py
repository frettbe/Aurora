"""
Boîte de dialogue pour le mapping de colonnes lors de l'importation.

Ce module définit `MapColumnsDialog`, une fenêtre modale réutilisable qui
présente à l'utilisateur une liste de champs cibles (ex: les champs d'un livre)
et lui permet d'associer chacun de ces champs à une colonne provenant d'une
source externe (ex: un fichier Excel).
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ..services.translation_service import translate


class MapColumnsDialog(QDialog):
    """
    Dialogue pour associer des champs cibles à des colonnes sources.

    Cette fenêtre génère dynamiquement un formulaire où chaque champ cible
    est associé à une liste déroulante contenant les noms des colonnes sources.
    Elle tente également de pré-remplir les choix en se basant sur une
    similarité de noms.
    """

    def __init__(
        self,
        parent: QWidget | None,
        source_columns: list[str],
        target_fields: list[str],
        title: str = "Correspondance des colonnes",
    ):
        """
        Initialise le dialogue de mapping.

        Args:
            parent: Le widget parent.
            source_columns: La liste des noms de colonnes du fichier source (ex: Excel).
            target_fields: La liste des noms de champs de la base de données à mapper.
            title: Le titre de la fenêtre.
        """
        super().__init__(parent)
        self.setWindowTitle(translate("map_columns_dialog.title"))

        # --- État interne ---
        # Ajoute une option pour ne mapper aucune colonne
        self._source_columns = [translate("map_columns_dialog.ignore_option")] + source_columns
        self._target_fields = target_fields
        # Dictionnaire pour stocker les QComboBox créées
        self._combos: dict[str, QComboBox] = {}

        # --- Construction de l'UI ---
        self._setup_ui()
        self._populate_and_guess_mappings()
        self._connect_signals()

    def _setup_ui(self):
        """Construit les widgets et les layouts de la fenêtre."""
        main_layout = QVBoxLayout(self)

        info_label = QLabel(translate("map_columns_dialog.info_label"))
        main_layout.addWidget(info_label)

        self.form_layout = QFormLayout()
        main_layout.addLayout(self.form_layout)

        tip_label = QLabel(translate("map_columns_dialog.tip_label"))
        tip_label.setStyleSheet("font-style: italic; color: #555;")
        main_layout.addWidget(tip_label)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        main_layout.addWidget(self.button_box)

    def _populate_and_guess_mappings(self):
        """Crée les QComboBox pour chaque champ cible et tente de deviner la sélection."""
        for field in self._target_fields:
            combo = QComboBox()
            combo.addItems(self._source_columns)

            # Tente de trouver la meilleure correspondance pour ce champ
            guess_index = self._guess_column_index(field)
            combo.setCurrentIndex(guess_index)

            self.form_layout.addRow(f"{field} :", combo)
            self._combos[field] = combo
