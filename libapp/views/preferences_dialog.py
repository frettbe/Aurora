"""
Boîte de dialogue pour la configuration des préférences de l'application.

Ce module définit `PreferencesDialog`, une fenêtre modale qui permet à
l'utilisateur de modifier divers paramètres de l'application, tels que la
langue, la vue de démarrage, et d'autres options de comportement.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QLabel,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..services.preferences import Preferences, save_preferences
from ..services.translation_service import translate

logger = logging.getLogger(__name__)


class PreferencesDialog(QDialog):
    """
    Fenêtre modale pour l'édition des préférences utilisateur.

    Elle est initialisée avec un objet `Preferences` existant. Si l'utilisateur
    valide, un nouvel objet `Preferences` mis à jour est stocké dans l'attribut
    `self.result` avant la fermeture du dialogue.
    """

    def __init__(self, parent: QWidget | None, *, prefs: Preferences):
        """Initialise le dialogue des préférences.

        Args:
            parent: Le widget parent.
            prefs: L'objet de préférences actuel à afficher et modifier.
                Il doit être fourni comme argument mot-clé.
        """
        super().__init__(parent)
        self.setWindowTitle(translate("preferences.title"))

        # --- État interne ---
        self._initial_prefs = prefs
        self._initial_language = prefs.language
        self.result: Preferences | None = None

        # --- Construction de l'UI ---
        self._setup_ui()
        self._load_initial_preferences(prefs)
        self._connect_signals()

    def _setup_ui(self):
        """Construit les widgets et les layouts de la fenêtre."""
        main_layout = QVBoxLayout(self)

        # ========================================
        # 🎨 SECTION 1 : APPARENCE
        # ========================================
        appearance_label = QLabel(translate("preferences.section_appearance"))
        appearance_label.setStyleSheet("font-weight: bold; font-size: 12pt; margin-top: 10px;")
        main_layout.addWidget(appearance_label)

        appearance_form = QFormLayout()

        # Thème
        self.theme_combo = QComboBox(self)
        appearance_form.addRow(f"<b>{translate('preferences.theme')}:</b>", self.theme_combo)

        # Langue
        self.language_combo = QComboBox(self)
        appearance_form.addRow(f"<b>{translate('preferences.language')}:</b>", self.language_combo)

        main_layout.addLayout(appearance_form)

        # Séparateur
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.HLine)
        separator1.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator1)

        # ========================================
        # 🖥️ SECTION 2 : INTERFACE
        # ========================================
        interface_label = QLabel(translate("preferences.section_interface"))
        interface_label.setStyleSheet("font-weight: bold; font-size: 12pt; margin-top: 10px;")
        main_layout.addWidget(interface_label)

        interface_form = QFormLayout()

        # Vue au démarrage
        self.startup_view_combo = QComboBox(self)
        interface_form.addRow(
            f"<b>{translate('preferences.startup_view')}:</b>", self.startup_view_combo
        )
        # Mémoriser géométrie
        self.remember_geometry_checkbox = QCheckBox()
        self.remember_geometry_checkbox.setText(translate("preferences.remember_geometry_label"))
        interface_form.addRow("", self.remember_geometry_checkbox)

        main_layout.addLayout(interface_form)

        # Séparateur
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator2)

        # ========================================
        # 📊 SECTION 3 : COLONNES VISIBLES
        # ========================================
        columns_label = QLabel(translate("preferences.section_columns"))
        columns_label.setStyleSheet("font-weight: bold; font-size: 12pt; margin-top: 10px;")
        main_layout.addWidget(columns_label)

        # Créer les checkboxes pour les colonnes
        self.column_checkboxes = {}
        all_columns = {
            "id": translate("column.id"),
            "code": translate("column.code"),
            "title": translate("column.title"),
            "volume": translate("column.volume"),
            "author": translate("column.author"),
            "year": translate("column.year"),
            "isbn": translate("column.isbn"),
            "publisher": translate("column.publisher"),
            "fund": translate("column.fund"),
            "available": translate("column.available"),
            "summary": translate("column.summary"),
            "cover_image": translate("column.cover_image"),
        }

        # Colonnes obligatoires (non décochables)
        mandatory_cols = ["title", "author"]

        for col_key, col_label in all_columns.items():
            cb = QCheckBox(col_label)
            if col_key in mandatory_cols:
                cb.setDisabled(True)  # Grisé, toujours coché
            self.column_checkboxes[col_key] = cb
            main_layout.addWidget(cb)

        # Séparateur
        separator3 = QFrame()
        separator3.setFrameShape(QFrame.HLine)
        separator3.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator3)

        # ========================================
        # 🔔 SECTION 4 : ALERTES & NOTIFICATIONS
        # ========================================
        alerts_label = QLabel(translate("preferences.section_alerts"))
        alerts_label.setStyleSheet("font-weight: bold; font-size: 12pt; margin-top: 10px;")
        main_layout.addWidget(alerts_label)

        # Alerte retards au démarrage
        self.cb_overdue_alert = QCheckBox(translate("preferences.show_overdue_alert"))
        main_layout.addWidget(self.cb_overdue_alert)

        # Espace avant les boutons
        main_layout.addSpacing(20)

        # Séparateur
        separator4 = QFrame()
        separator4.setFrameShape(QFrame.HLine)
        separator4.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator4)

        # ========================================
        # 📚 SECTION 5 : PRÊTS (Simplifié)
        # ========================================
        loan_label = QLabel(translate("preferences.section_loans"))
        loan_label.setStyleSheet("font-weight: bold; font-size: 12pt; margin-top: 10px;")
        main_layout.addWidget(loan_label)

        loan_form = QFormLayout()

        # Durée de prêt par défaut
        self.spin_default_loan_days = QSpinBox()
        self.spin_default_loan_days.setRange(1, 365)
        self.spin_default_loan_days.setSuffix(" " + translate("preferences.days"))
        loan_form.addRow(
            f"{translate('preferences.default_loan_days')}:", self.spin_default_loan_days
        )

        main_layout.addLayout(loan_form)

        # Espace avant les boutons
        main_layout.addSpacing(20)

        # ========================================
        # BOUTONS OK/ANNULER
        # ========================================
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText(
            translate("buttons.save")
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(
            translate("buttons.cancel")
        )
        main_layout.addWidget(self.button_box)

    def _load_initial_preferences(self, prefs: Preferences):
        """Charge les valeurs depuis l'objet `Preferences` et peuple les widgets."""
        # --- Chargement dynamique des langues ---
        try:
            lang_dir = Path(__file__).parent.parent.parent / "lang"
            lang_files = sorted([f.stem for f in lang_dir.glob("*.yaml")])
            self.language_combo.addItems(lang_files)
        except Exception:
            self.language_combo.addItems(["en", "fr"])  # Fallback

        self.language_combo.setCurrentText(prefs.language)

        # --- Autres préférences ---
        self.startup_view_combo.addItems(["dashboard", "books", "members", "loans", "split"])
        self.startup_view_combo.setCurrentText(prefs.startup_view)
        self.remember_geometry_checkbox.setChecked(prefs.remember_window_geometry)

        self.theme_combo.addItems(["auto", "light", "dark"])
        self.theme_combo.setCurrentText(prefs.theme)

        # Charger l'état des checkboxes colonnes
        for col_key, checkbox in self.column_checkboxes.items():
            checkbox.setChecked(col_key in prefs.books_visible_columns)

        self.cb_overdue_alert.setChecked(prefs.show_overdue_alert_on_startup)

        # Charger la durée de prêt par défaut
        self.spin_default_loan_days.setValue(prefs.default_loan_days)

    @Slot()
    def _on_accept(self):
        """Sauvegarde les nouvelles préférences et ferme le dialogue."""
        new_language = self.language_combo.currentText()
        new_startup = self.startup_view_combo.currentText()
        new_theme = self.theme_combo.currentText()
        visible_cols = [col_key for col_key, cb in self.column_checkboxes.items() if cb.isChecked()]
        show_overdue = self.cb_overdue_alert.isChecked()

        # Crée un nouvel objet Preferences mis à jour
        self.result = Preferences(
            language=new_language,
            startup_view=new_startup,
            theme=new_theme,
            remember_window_geometry=self.remember_geometry_checkbox.isChecked(),
            main_window_geometry=getattr(self._initial_prefs, "main_window_geometry", None),
            import_last_directory=getattr(self._initial_prefs, "import_last_directory", None),
            import_last_mapping=getattr(self._initial_prefs, "import_last_mapping", {}),
            books_view_state=getattr(self._initial_prefs, "books_view_state", {}),
            members_view_state=getattr(self._initial_prefs, "members_view_state", {}),
            loans_view_state=getattr(self._initial_prefs, "loans_view_state", {}),
            books_visible_columns=visible_cols,
            members_visible_columns=getattr(self._initial_prefs, "members_visible_columns", []),
            loans_visible_columns=getattr(self._initial_prefs, "loans_visible_columns", []),
            export_include_date=getattr(self._initial_prefs, "export_include_date", True),
            export_include_count=getattr(self._initial_prefs, "export_include_count", True),
            export_include_custom_message=getattr(
                self._initial_prefs, "export_include_custom_message", False
            ),
            export_last_custom_message=getattr(
                self._initial_prefs, "export_last_custom_message", ""
            ),
            export_last_format=getattr(self._initial_prefs, "export_last_format", "xlsx"),
            export_last_columns_books=getattr(self._initial_prefs, "export_last_columns_books", []),
            export_last_columns_members=getattr(
                self._initial_prefs, "export_last_columns_members", []
            ),
            library_name=getattr(self._initial_prefs, "library_name", ""),
            library_name_enabled=getattr(self._initial_prefs, "library_name_enabled", False),
            app_name=getattr(self._initial_prefs, "app_name", "Aurora"),
            app_name_custom=getattr(self._initial_prefs, "app_name_custom", False),
            show_overdue_alert_on_startup=show_overdue,
            default_loan_days=self.spin_default_loan_days.value(),
        )

        # Message pour changement de langue
        if new_language != self._initial_language:
            QMessageBox.information(
                self,
                translate("preferences.language_changed_title"),
                translate("preferences.language_changed_body"),
            )

        try:
            # Sauvegarder IMMÉDIATEMENT (feedback utilisateur)
            save_preferences(self.result)
            super().accept()
        except Exception as e:
            logger.error(f"Erreur sauvegarde préferences: {e}")
            QMessageBox.critical(
                self,
                translate("preferences.error_title"),
                f"{translate('preferences.error_save')}: {str(e)}",
            )

    def _connect_signals(self):
        """Connecte les signaux des boutons aux slots."""
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self._on_reject)

    @Slot()
    def _on_reject(self):
        """Annule les modifications et ferme le dialogue."""
        self.result = None
        self.reject()
