"""
Boîte de dialogue modale pour la sélection d'une notice bibliographique.

Ce module est utilisé lorsque une recherche externe (comme celle de la BnF)
retourne plusieurs résultats possibles pour une même requête (par exemple, un ISBN).
Il présente ces résultats à l'utilisateur et lui permet d'en choisir un.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from ..services.translation_service import translate

# On pourrait utiliser un BookDTO ici, mais un dict est plus flexible
# si les sources API changent.
BnfNotice = dict[str, str]


class BnfSelectDialog(QDialog):
    """
    Affiche une liste de notices bibliographiques pour la sélection.

    La fenêtre est modale. Après sa fermeture, l'attribut `self.selected_notice`
    contiendra la notice choisie par l'utilisateur (un dictionnaire) si le
    dialogue a été accepté, sinon il sera `None`.
    """

    def __init__(self, parent=None, items: list[BnfNotice] | None = None):
        """
        Initialise la boîte de dialogue.

        Args:
            parent: Le widget parent de cette fenêtre.
            items: Une liste de dictionnaires, chaque dictionnaire représentant
                   une notice de livre trouvée.
        """
        super().__init__(parent)
        self.setWindowTitle(translate("bnf_select.title"))

        # Attribut public pour stocker le résultat
        self.selected_notice: BnfNotice | None = None

        items = items or []

        # --- Création des widgets et du layout ---
        v_layout = QVBoxLayout(self)
        v_layout.addWidget(QLabel(translate("bnf_select.multiple_results")))

        self.list_widget = QListWidget()
        for notice in items:
            # Construit une ligne lisible pour l'affichage
            title = notice.get("title", translate("bnf_select.unknown_title"))
            author = notice.get("author", translate("bnf_select.unknown_author"))
            year = notice.get("year", "N/A")
            line = f"{title} — {author} ({year})"
            if isbn := notice.get("isbn"):
                line += f" [ISBN {isbn}]"

            list_item = QListWidgetItem(line)
            # Astuce : on stocke la notice complète (le dict) dans l'item
            list_item.setData(Qt.UserRole, notice)
            self.list_widget.addItem(list_item)

        v_layout.addWidget(self.list_widget)

        # --- Boutons OK/Annuler ---
        h_buttons_layout = QHBoxLayout()
        btn_ok = QPushButton(translate("buttons.choose"))
        btn_cancel = QPushButton(translate("buttons.cancel"))
        h_buttons_layout.addStretch()
        h_buttons_layout.addWidget(btn_ok)
        h_buttons_layout.addWidget(btn_cancel)
        v_layout.addLayout(h_buttons_layout)

        # --- Connexion des signaux ---
        btn_ok.clicked.connect(self._on_accept)
        btn_cancel.clicked.connect(self.reject)
        # Permet de valider avec un double-clic sur un item
        self.list_widget.itemDoubleClicked.connect(self._on_accept)

    def _on_accept(self):
        """
        Gère la validation du dialogue.

        Récupère la notice complète stockée dans l'item sélectionné, la place
        dans `self.selected_notice` et ferme le dialogue avec un statut "Accepté".
        """
        current_item = self.list_widget.currentItem()
        if not current_item:
            # Si aucun item n'est sélectionné, on ne fait rien ou on pourrait
            # afficher un message, mais le plus simple est de ne pas valider.
            return

        self.selected_notice = current_item.data(Qt.UserRole)
        self.accept()
