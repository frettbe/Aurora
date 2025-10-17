"""
Vue principale du tableau de bord (Dashboard).

Ce module définit la `DashboardView`, qui sert de page d'accueil à
l'application. Elle affiche des statistiques clés (KPIs) sur l'état de la
bibliothèque et fournit des raccourcis vers les actions les plus courantes.
"""

from __future__ import annotations

from datetime import date
from functools import partial

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
from sqlalchemy import func, select

from ..persistence.database import get_session
from ..persistence.models_sa import Book, Loan, LoanStatus, Member
from ..services.translation_service import translate
from ..utils.icon_helper import toolbar_icon


def _to_int(value: any) -> int:
    """Convertit une valeur en entier de manière sécurisée, avec 0 par défaut."""
    try:
        return int(value or 0)
    except (ValueError, TypeError):
        return 0


class ClickableLabel(QLabel):
    """
    Un QLabel personnalisé qui émet un signal `clicked` lorsqu'on clique dessus.

    Il est stylisé pour ressembler à un lien hypertexte afin d'inciter à l'action.
    """

    clicked = Signal()

    def __init__(self, text: str = "", parent: QWidget | None = None):
        """Initialise le label cliquable."""
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("color: #2e86c1; text-decoration: underline;")

    def mousePressEvent(self, event):
        """Émet le signal `clicked` lors d'un clic de souris."""
        self.clicked.emit()
        super().mousePressEvent(event)


class DashboardView(QWidget):
    """
    Widget principal du tableau de bord.

    Cette vue affiche un résumé de l'état de la bibliothèque (nombre de livres,
    de membres, de prêts en cours, etc.) et des boutons d'action rapide.
    Elle est conçue pour être "stupide" : elle affiche les données et émet des
    signaux vers la MainWindow, qui contient la logique de l'application.

    Signals:
        newBookRequested: Demandé lors du clic sur "Nouveau Livre".
        newMemberRequested: Demandé lors du clic sur "Nouveau Membre".
        newLoanRequested: Demandé lors du clic sur "Nouveau Prêt".
        filterLoansRequested (str, bool): Demande l'affichage de la liste des prêts
                                          avec un filtre. Le booléen indique si
                                          seuls les retards doivent être montrés.
        detachRequested: Demandé lorsque l'utilisateur veut détacher la vue.
    """

    # --- Déclaration des signaux émis par la vue ---
    newBookRequested = Signal()
    newMemberRequested = Signal()
    newLoanRequested = Signal()
    filterLoansRequested = Signal(str, bool)  # (status_filter, overdue_only)
    detachRequested = Signal()
    showMembersRequested = Signal()

    def __init__(self, parent: QWidget | None = None):
        """Initialise la vue du tableau de bord."""
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()
        self.refresh()

    def _setup_ui(self):
        """Construit l'interface utilisateur du tableau de bord."""
        root_layout = QVBoxLayout(self)

        # --- Barre de titre avec bouton "Détacher" ---
        title_bar_layout = QHBoxLayout()
        title_label = QLabel(translate("dashboard.view_title"))
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        title_bar_layout.addWidget(title_label)
        title_bar_layout.addStretch()
        self.detach_button = QPushButton(
            icon=toolbar_icon("arrow-square-out")  # Icône "détacher/ouvrir dans nouvelle fenêtre"
        )
        self.detach_button.setToolTip(translate("dashboard.detach_tooltip"))
        self.detach_button.setVisible(False)
        self.detach_button.setFixedSize(24, 24)
        title_bar_layout.addWidget(self.detach_button)
        root_layout.addLayout(title_bar_layout)

        # --- Grille pour les indicateurs clés (KPIs) ---
        kpi_widget = QWidget(self)
        self.kpi_grid = QGridLayout(kpi_widget)
        self.kpi_grid.setContentsMargins(20, 30, 20, 30)  # Plus de marges
        self.kpi_grid.setHorizontalSpacing(50)  # Plus d'espace horizontal
        self.kpi_grid.setVerticalSpacing(20)  # Plus d'espace vertical
        root_layout.addWidget(kpi_widget)

        # --- Barre d'actions rapides ---
        actions_layout = QHBoxLayout()
        self.new_book_button = QPushButton(translate("dashboard.new_book_button"))
        self.new_member_button = QPushButton(translate("dashboard.new_member_button"))
        self.new_loan_button = QPushButton(translate("dashboard.new_loan_button"))
        actions_layout.addWidget(self.new_book_button)
        actions_layout.addWidget(self.new_member_button)
        actions_layout.addWidget(self.new_loan_button)
        actions_layout.addStretch()
        self.new_book_button.setVisible(False)
        self.new_member_button.setVisible(False)
        self.new_loan_button.setVisible(False)
        root_layout.addLayout(actions_layout)

    def _connect_signals(self):
        """Connecte les signaux des widgets internes aux slots ou signaux de la vue."""
        self.detach_button.clicked.connect(self.detachRequested)
        self.new_book_button.clicked.connect(self.newBookRequested)
        self.new_member_button.clicked.connect(self.newMemberRequested)
        self.new_loan_button.clicked.connect(self.newLoanRequested)

    @Slot()
    def refresh(self) -> None:
        """
        Orchestre le rafraîchissement complet de la vue.

        Cette méthode est le point d'entrée public pour mettre à jour le tableau
        de bord. Elle récupère les dernières statistiques et met à jour l'affichage.
        """
        try:
            stats = self._compute_kpis()
            self._update_display(stats)
        except Exception as e:
            print(f"Erreur critique lors du rafraîchissement du dashboard: {e}")
            # En cas d'erreur (ex: DB non accessible), on affiche des zéros
            self._update_display((0,) * 6)

    def _update_display(self, stats: tuple[int, ...]):
        """Met à jour les widgets d'affichage avec les nouvelles statistiques."""
        (books_count, copies_total, copies_available, members_count, loans_open, overdues_count) = (
            stats
        )

        # Nettoie la grille avant de la reconstruire pour éviter les doublons
        while self.kpi_grid.count():
            item = self.kpi_grid.takeAt(0)
            if widget := item.widget():
                widget.deleteLater()

        # --- Création et affichage des nouveaux KPIs ---
        availability_rate = round(100 * copies_available / copies_total) if copies_total > 0 else 0

        self._create_kpi_widget(translate("dashboard.kpi.books_label"), str(books_count), 0, 0)
        self._create_kpi_widget(
            translate("dashboard.kpi.copies_total_label"), str(copies_total), 0, 1
        )
        self._create_kpi_widget(
            translate("dashboard.kpi.copies_available_label"), str(copies_available), 0, 2
        )
        self._create_kpi_widget(
            translate("dashboard.kpi.availability_label"), f"{availability_rate}%", 0, 3
        )

        members_label = ClickableLabel(str(members_count))
        members_label.clicked.connect(self._on_members_clicked)  # 🔥 Connecter à un nouveau signal
        self._create_kpi_widget(translate("dashboard.kpi.members_label"), members_label, 2, 0)

        # KPI cliquable pour les prêts ouverts
        open_loans_label = ClickableLabel(str(loans_open))
        open_loans_label.clicked.connect(
            partial(self.filterLoansRequested.emit, "Prêts ouverts", False)
        )
        self._create_kpi_widget(translate("dashboard.kpi.open_loans_label"), open_loans_label, 2, 1)

        # KPI cliquable pour les retards
        overdues_label = ClickableLabel(str(overdues_count))
        overdues_label.clicked.connect(
            partial(self.filterLoansRequested.emit, "Prêts en retard", True)
        )
        if overdues_count > 0:
            overdues_label.setStyleSheet("font-size:20px; font-weight:600; color:red;")
        self._create_kpi_widget(translate("dashboard.kpi.overdues_label"), overdues_label, 2, 2)

    def _create_kpi_widget(self, label_text: str, value_widget: QWidget | str, row: int, col: int):
        """Crée une paire de widgets (libellé + valeur) et les place dans la grille."""
        label = QLabel(label_text)
        label.setStyleSheet("color:#666")

        if isinstance(value_widget, str):
            value = QLabel(value_widget)
            value.setStyleSheet("font-size:28px; font-weight:600;")
        else:
            value = value_widget  # C'est déjà un widget (ex: ClickableLabel)
            if (
                not value.styleSheet()
            ):  # Applique le style par défaut si pas déjà stylisé (ex: en rouge)
                value.setStyleSheet("font-size:28px; font-weight:600;")

        self.kpi_grid.addWidget(label, row, col, Qt.AlignLeft)
        self.kpi_grid.addWidget(value, row + 1, col, Qt.AlignLeft)

    def _compute_kpis(self) -> tuple[int, int, int, int, int, int]:
        """
        Récupère toutes les statistiques brutes depuis la base de données
        en une seule transaction.

        Returns:
            Un tuple contenant dans l'ordre : nombre de livres, total des exemplaires,
            exemplaires disponibles, nombre de membres, prêts ouverts, prêts en retard.
        """
        today = date.today()
        with get_session() as s:
            books_count = s.scalar(select(func.count(Book.id)))
            members_count = s.scalar(select(func.count(Member.id)))
            copies_total = s.scalar(select(func.coalesce(func.sum(Book.copies_total), 0)))
            copies_available = s.scalar(select(func.coalesce(func.sum(Book.copies_available), 0)))
            loans_open = s.scalar(select(func.count(Loan.id)).where(Loan.status == LoanStatus.open))
            overdues_count = s.scalar(
                select(func.count(Loan.id)).where(
                    Loan.status == LoanStatus.open, Loan.due_date < today
                )
            )

            return (
                _to_int(books_count),
                _to_int(copies_total),
                _to_int(copies_available),
                _to_int(members_count),
                _to_int(loans_open),
                _to_int(overdues_count),
            )

    def _on_members_clicked(self):
        """Émet le signal pour afficher la liste des membres."""
        self.showMembersRequested.emit()
