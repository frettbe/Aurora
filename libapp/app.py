"""
Module principal de l'application Biblio.

Contient la MainWindow, qui agit comme le chef d'orchestre de l'application,
gérant les vues, les actions, les menus, et la communication entre les composants.
"""

from __future__ import annotations

import logging
import sys

import qdarktheme
from PySide6.QtCore import QByteArray, QCoreApplication, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QToolBar,
)

from .persistence.database import ensure_tables, get_session
from .persistence.models_sa import Book, Member
from .services.enhanced_logging_config import setup_app_logging
from .services.preferences import load_preferences, save_preferences
from .services.translation_service import set_language, translate
from .utils.icon_helper import app_icon, toolbar_icon
from .views.about_dialog import AboutDialog
from .views.book_details_panel import BookDetailsPanel
from .views.book_editor import BookEditor
from .views.book_list import BookListView
from .views.dashboard import DashboardView
from .views.import_dialog import ImportDialog
from .views.import_members_dialog import ImportMembersDialog
from .views.loan_dialog import LoanDialog
from .views.loan_dialogs import ReturnLoanDialog
from .views.loan_list import LoanListView
from .views.member_details_panel import MemberDetailsPanel
from .views.member_editor import MemberEditor
from .views.member_list import MemberListView
from .views.preferences_dialog import PreferencesDialog

setup_app_logging(console_output=True)

logging.basicConfig(
    level=logging.DEBUG,  # Pour obtenir un max d'infos
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Fenêtre principale de l'application."""

    dataChanged = Signal()

    def __init__(self, parent=None):
        """Initialise la fenêtre principale."""
        super().__init__(parent)
        self._load_config_and_translate()
        self.setWindowTitle(translate("window.title"))
        self.setWindowIcon(app_icon())
        self.resize(1200, 800)
        self._create_actions()
        self._create_main_widgets()
        self._create_menus()
        self._create_toolbars()
        self._create_status_bar()
        self._connect_signals()
        self._restore_state()
        self._check_overdue_on_startup()

    def _check_overdue_on_startup(self):
        """
        Vérifie les prêts en retard au démarrage et affiche une alerte si activé.
        """
        # Vérifier si l'alerte est activée
        if not self.prefs.show_overdue_alert_on_startup:
            return

        # Importer les dépendances
        from .services.loan_service import get_overdue_count
        from .views.overdue_alert_dialog import OverdueAlertDialog

        # Compter les retards
        overdue_count = get_overdue_count()

        # Afficher l'alerte seulement s'il y a des retards
        if overdue_count > 0:
            dialog = OverdueAlertDialog(overdue_count, self)
            dialog.viewOverduesRequested.connect(self._show_overdues_from_alert)
            dialog.exec()

    def _show_overdues_from_alert(self):
        """
        Affiche la liste des prêts filtrée sur les retards.

        Appelé depuis le dialog d'alerte.
        """
        # Changer vers la vue prêts
        self.show_loan_list()

        # Appliquer le filtre retards (utilise le signal existant du dashboard)
        if hasattr(self.loan_list_view, "filter_overdue"):
            self.loan_list_view.filter_overdue()

    def _load_config_and_translate(self):
        """Charge les préférences et applique la langue."""
        self.prefs = load_preferences()
        set_language(self.prefs.language)

        # Appliquer le thème au démarrage
        try:
            logger.info(f"📱 Application du thème initial : {self.prefs.theme}")

            # 🎯 Enregistrer le thème
            from .utils.icon_helper import set_current_theme

            set_current_theme(self.prefs.theme)

            # Appliquer
            qdarktheme.setup_theme(self.prefs.theme)
        except Exception as e:
            logger.error(f"❌ Erreur application thème initial : {e}")

    def _create_actions(self):
        """Crée toutes les actions de l'application."""

        # ════════════════════════════════════════════════════════════
        # ACTIONS PRINCIPALES (avec icônes Phosphor)
        # ════════════════════════════════════════════════════════════

        # Nouveau livre
        self.act_new_book = QAction(
            toolbar_icon("book-open-text"), translate("menu.file_new_book"), self
        )
        self.act_new_book.setShortcut(QKeySequence.StandardKey.New)
        self.act_new_book.triggered.connect(self.add_book)

        # Nouveau membre
        self.act_new_member = QAction(
            toolbar_icon("user-plus"), translate("menu.file_new_member"), self
        )
        self.act_new_member.setShortcut(QKeySequence("Ctrl+M"))
        self.act_new_member.triggered.connect(self.add_member)

        # Nouvel emprunt
        self.act_new_loan = QAction(
            toolbar_icon("calendar-plus"), translate("menu.file_new_loan"), self
        )
        self.act_new_loan.setShortcut(QKeySequence("Ctrl+L"))
        self.act_new_loan.triggered.connect(self.new_loan)

        # Importer
        self.act_import = QAction(
            toolbar_icon("download-simple"), translate("menu.file_import"), self
        )
        self.act_import.setShortcut(QKeySequence("Ctrl+I"))
        self.act_import.triggered.connect(self.import_books)

        # Importer membres
        self.act_import_members = QAction(
            toolbar_icon("file-arrow-up"), translate("action.import_members"), self
        )
        self.act_import.setShortcut(QKeySequence("Ctrl+D"))
        self.act_import_members.triggered.connect(self._on_import_members)

        # Exporter (si tu l'utilises)
        self.act_export = QAction(toolbar_icon("upload-simple"), translate("context.export"), self)
        self.act_export.setShortcut(QKeySequence("Ctrl+Shift+E"))
        self.act_export.triggered.connect(self.export_current_view)  # Si tu as cette méthode

        # Rechercher
        self.act_search = QAction(
            toolbar_icon("magnifying-glass"), translate("book_list.search_label"), self
        )
        self.act_search.setShortcut(QKeySequence.StandardKey.Find)
        # self.act_search.triggered.connect(self.show_search)  # Si tu as cette méthode

        # Éditer (contextuel)
        self.act_edit_item = QAction(toolbar_icon("pencil-simple"), translate("menu.edit"), self)
        self.act_edit_item.setEnabled(False)  # Activé quand un élément est sélectionné

        # Supprimer (contextuel)
        self.act_delete_item = QAction(
            toolbar_icon("trash"), translate("menu.edit_delete_item"), self
        )
        self.act_delete_item.setEnabled(False)  # Activé quand un élément est sélectionné

        # Préférences
        self.act_preferences = QAction(toolbar_icon("gear"), translate("preferences.title"), self)
        self.act_preferences.setShortcut(QKeySequence("Ctrl+,"))
        self.act_preferences.triggered.connect(self.open_preferences)

        # À propos
        self.act_about = QAction(toolbar_icon("info"), translate("menu.about"), self)
        self.act_about.setShortcut(QKeySequence("F1"))
        self.act_about.triggered.connect(self.show_about)

        # ════════════════════════════════════════════════════════════
        # AUTRES ACTIONS (sans icônes, juste texte)
        # ════════════════════════════════════════════════════════════

        # Rafraîchir
        self.act_refresh = QAction(
            toolbar_icon("arrow-clockwise"),  # 🎯 ICÔNE
            translate("tooltip.refresh"),
            self,
        )
        self.act_refresh.setShortcut(QKeySequence.StandardKey.Refresh)
        self.act_refresh.triggered.connect(self.refresh_all_views)

        # Quitter
        self.act_quit = QAction(
            toolbar_icon("x"),  # 🎯 ICÔNE (ou "sign-out" si tu préfères)
            translate("menu.file_quit"),
            self,
        )
        self.act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        self.act_quit.triggered.connect(self.close)

        # Retourner emprunt
        self.act_return_loan = QAction(
            toolbar_icon("arrow-u-up-left"),  # 🔥 AJOUT DE L'ICÔNE
            translate("menu.edit_return"),
            self,
        )
        self.act_return_loan.triggered.connect(self.return_loan)

        # Documentation
        self.act_docs = QAction(
            toolbar_icon("question"),  # 🎯 ICÔNE (ou "book-open" ou "lifebuoy")
            translate("menu.help"),
            self,
        )
        self.act_docs.triggered.connect(self.online_help)

        # Vues (Dashboard, Books, Members, Loans, Split)
        self.act_show_dashboard = QAction(
            toolbar_icon("chart-pie"),  # 🎯 ICÔNE
            translate("menu.view_dashboard"),
            self,
        )
        self.act_show_dashboard.triggered.connect(self.show_dashboard)

        self.act_show_books = QAction(
            toolbar_icon("books"),  # 🎯 ICÔNE
            translate("menu.view_books"),
            self,
        )
        self.act_show_books.triggered.connect(self.show_book_list)

        self.act_show_members = QAction(
            toolbar_icon("users"),  # 🎯 ICÔNE
            translate("menu.view_members"),
            self,
        )
        self.act_show_members.triggered.connect(self.show_member_list)

        self.act_show_loans = QAction(
            toolbar_icon("hand-coins"),  # 🎯 ICÔNE
            translate("menu.view_loans"),
            self,
        )
        self.act_show_loans.triggered.connect(self.show_loan_list)

        self.act_show_split = QAction(
            toolbar_icon("columns"),  # 🎯 ICÔNE
            translate("menu.view_split"),
            self,
        )
        self.act_show_split.triggered.connect(self.show_split_view)

    def _create_main_widgets(self):
        """Crée et configure le widget central avec splitter pour détails."""
        # Stack principal (vues liste/dashboard)
        self.stack = QStackedWidget(self)

        self.dashboard_view = DashboardView(parent=self)
        self.book_list_view = BookListView(parent=self, prefs=self.prefs)
        self.member_list_view = MemberListView(parent=self, prefs=self.prefs)
        self.loan_list_view = LoanListView(parent=self, prefs=self.prefs)

        # Splitter mode split view (code existant à garder)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.book_list_split = BookListView(parent=self.splitter, prefs=self.prefs)
        self.member_list_split = MemberListView(parent=self.splitter, prefs=self.prefs)
        self.splitter.addWidget(self.book_list_split)
        self.splitter.addWidget(self.member_list_split)
        self.splitter.setChildrenCollapsible(False)

        self.stack.addWidget(self.dashboard_view)
        self.stack.addWidget(self.book_list_view)
        self.stack.addWidget(self.member_list_view)
        self.stack.addWidget(self.loan_list_view)
        self.stack.addWidget(self.splitter)

        # 🎯 NOUVEAU : Stack pour panneaux détails
        self.details_stack = QStackedWidget(self)
        self.book_details_panel = BookDetailsPanel(self)
        self.member_details_panel = MemberDetailsPanel(self)

        self.details_stack.addWidget(self.book_details_panel)
        self.details_stack.addWidget(self.member_details_panel)

        # 🎯 NOUVEAU : Splitter horizontal global (vues principales + détails)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.main_splitter.addWidget(self.stack)
        self.main_splitter.addWidget(self.details_stack)
        self.main_splitter.setStretchFactor(0, 2)  # Stack principal = 2/3
        self.main_splitter.setStretchFactor(1, 1)  # Détails = 1/3
        self.main_splitter.setChildrenCollapsible(False)

        self.setCentralWidget(self.main_splitter)  # ← Changé de self.stack à self.main_splitter

    def _create_menus(self):
        """Crée la barre de menus."""
        menu_bar = self.menuBar()
        menu_file = menu_bar.addMenu(translate("menu.file"))
        menu_file.addAction(self.act_new_book)
        menu_file.addAction(self.act_new_member)
        menu_file.addAction(self.act_new_loan)
        menu_file.addSeparator()
        menu_file.addAction(self.act_import)
        menu_file.addAction(self.act_import_members)
        menu_file.addAction(self.act_export)
        menu_file.addSeparator()
        menu_file.addAction(self.act_refresh)
        menu_file.addSeparator()
        menu_file.addAction(self.act_quit)
        menu_edit = menu_bar.addMenu(translate("menu.edit"))
        menu_edit.addAction(self.act_edit_item)
        menu_edit.addAction(self.act_delete_item)
        menu_edit.addSeparator()
        menu_edit.addAction(self.act_return_loan)
        menu_edit.addSeparator()
        menu_edit.addAction(self.act_preferences)
        menu_view = menu_bar.addMenu(translate("menu.view"))
        menu_view.addAction(self.act_show_dashboard)
        menu_view.addAction(self.act_show_books)
        menu_view.addAction(self.act_show_members)
        menu_view.addAction(self.act_show_loans)
        menu_view.addAction(self.act_show_split)
        menu_help = menu_bar.addMenu(translate("menu.help"))
        menu_help.addAction(self.act_docs)
        menu_help.addAction(self.act_about)

    def _create_toolbars(self):
        """Crée la barre d'outils principale."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        toolbar.addAction(self.act_new_book)
        toolbar.addAction(self.act_new_member)
        toolbar.addAction(self.act_new_loan)
        toolbar.addSeparator()
        toolbar.addAction(self.act_show_dashboard)
        toolbar.addAction(self.act_show_books)
        toolbar.addAction(self.act_show_members)
        toolbar.addAction(self.act_show_loans)
        toolbar.addAction(self.act_show_split)
        toolbar.addSeparator()
        toolbar.addAction(self.act_import)
        toolbar.addAction(self.act_import_members)
        toolbar.addAction(self.act_export)
        toolbar.addSeparator()
        toolbar.addAction(self.act_refresh)
        toolbar.addAction(self.act_about)
        toolbar.addAction(self.act_quit)

    def _create_status_bar(self):
        """Crée une barre de statut simple."""
        self.statusBar().showMessage(translate("statusbar.ready"))

    def _connect_signals(self):
        """Connecte tous les signaux de l'application."""
        # Signaux des vues
        self.dataChanged.connect(self.refresh_all_views)
        self.stack.currentChanged.connect(self._on_view_changed)

        # Vues principales
        self.book_list_view.bookActivated.connect(self.edit_book_by_id)
        self.member_list_view.memberActivated.connect(self.edit_member_by_id)
        self.loan_list_view.loanActivated.connect(self.return_loan_by_id)

        # 🔥 Vues de la split view
        self.book_list_split.bookActivated.connect(self.edit_book_by_id)
        self.member_list_split.memberActivated.connect(self.edit_member_by_id)
        self.dashboard_view.showMembersRequested.connect(self.show_member_list)
        self.dashboard_view.filterLoansRequested.connect(self._on_filter_loans_from_dashboard)

        # 🎯 IMPORTANT : Connecter les sélections APRÈS que les vues soient chargées
        # On utilise QTimer pour différer la connexion
        from PySide6.QtCore import QTimer

        QTimer.singleShot(100, self._connect_selection_signals)

    def _restore_state(self):
        """Restaure la géométrie de la fenêtre et la vue de démarrage."""
        if (
            self.prefs.remember_window_geometry
            and hasattr(self.prefs, "main_window_geometry")
            and self.prefs.main_window_geometry
        ):
            self.restoreGeometry(self.prefs.main_window_geometry)

        # Application de la vue de démarrage D'ABORD
        startup_view = self.prefs.startup_view
        if startup_view == "dashboard":
            self.show_dashboard()
        elif startup_view == "books":
            self.show_book_list()
        elif startup_view == "members":
            self.show_member_list()
        elif startup_view == "loans":
            self.show_loan_list()
        elif startup_view == "split":
            self.show_split_view()
        else:
            # Fallback par défaut
            self.show_book_list()

        # 🎯 DÉPLACÉ ICI : Restaurer l'état du splitter APRÈS le chargement des vues
        if hasattr(self.prefs, "main_splitter_state") and self.prefs.main_splitter_state:
            splitter_bytes = QByteArray.fromBase64(self.prefs.main_splitter_state.encode())
            self.main_splitter.restoreState(splitter_bytes)

    # --- SLOTS ET MÉTHODES PUBLIQUES RESTAURÉS ---

    @Slot()
    def refresh_all_views(self):
        """Rafraîchit toutes les vues qui affichent des données."""
        # Ces refresh() vont gérer correctement les sessions maintenant
        self.dashboard_view.refresh()
        self.book_list_view.refresh()
        self.member_list_view.refresh()
        self.loan_list_view.refresh()

        # 🔧 BONUS : Refresh aussi les vues split si elles sont visibles
        if self.stack.currentWidget() == self.splitter:
            self.book_list_split.refresh()
            self.member_list_split.refresh()

    def show_dashboard(self):
        self.stack.setCurrentWidget(self.dashboard_view)
        self.main_splitter.widget(1).hide()
        self.dashboard_view.refresh()
        self._save_current_view("dashboard")

    def show_book_list(self):
        self.stack.setCurrentWidget(self.book_list_view)
        self.main_splitter.widget(1).show()
        self.details_stack.setCurrentWidget(self.book_details_panel)
        self.book_list_view.refresh()
        self._save_current_view("books")

    def show_member_list(self):
        self.stack.setCurrentWidget(self.member_list_view)
        self.main_splitter.widget(1).show()
        self.details_stack.setCurrentWidget(self.book_details_panel)
        self.member_list_view.refresh()
        self._save_current_view("members")

    def show_loan_list(self):
        self.stack.setCurrentWidget(self.loan_list_view)
        self.main_splitter.widget(1).hide()  # widget(1) = details_stack
        self.loan_list_view.refresh()
        self._save_current_view("loans")

    def show_split_view(self):
        """Affiche la vue splitée Books + Members."""
        self.stack.setCurrentWidget(self.splitter)
        self.main_splitter.widget(1).show()
        self.details_stack.setCurrentWidget(self.book_details_panel)
        self.book_list_split.refresh()
        self.member_list_split.refresh()
        self._save_current_view("split")

    def _save_current_view(self, view_name: str):
        """Sauvegarde la vue active dans les préférences."""
        if self.prefs.startup_view != view_name:
            self.prefs.startup_view = view_name
            save_preferences(self.prefs)

    @Slot()
    def add_book(self):
        dlg = BookEditor(self)
        if dlg.exec():
            self.dataChanged.emit()

    @Slot(int)
    def edit_book_by_id(self, book_id: int):
        """Édite un livre par son ID."""
        with get_session() as session:
            book = session.get(Book, book_id)
            if not book:
                return

            # 🔧 FIX : Détacher l'objet AVANT la fermeture de la session
            session.expunge(book)

        # Maintenant la session est fermée, mais book est accessible
        dlg = BookEditor(self, book=book)
        if dlg.exec():
            self.dataChanged.emit()

    @Slot()
    def add_member(self):
        dlg = MemberEditor(self)
        if dlg.exec():
            self.dataChanged.emit()

    @Slot()
    def _on_import_members(self):
        """Ouvre le dialog d'import de membres."""

        prefs = load_preferences()
        dialog = ImportMembersDialog(self, prefs)

        if dialog.exec():
            # Rafraîchir la liste
            self.refresh()

    @Slot(int)
    def edit_member_by_id(self, member_id: int):
        """Édite un membre par son ID."""
        with get_session() as session:
            member = session.get(Member, member_id)
            if not member:
                return

            # 🔧 FIX : Détacher l'objet AVANT la fermeture de la session
            session.expunge(member)

        # Maintenant la session est fermée, mais member est accessible
        dlg = MemberEditor(self, member=member)
        if dlg.exec():
            self.dataChanged.emit()

    @Slot()
    def new_loan(self):
        """Crée un nouveau prêt via le menu/bouton."""
        dlg = LoanDialog(self)  # Sans paramètres → les deux combos sont libres
        if dlg.exec():
            self.dataChanged.emit()

    @Slot()
    def return_loan(self):
        """Retourne un emprunt via le dialogue."""
        # Récupérer l'ID sélectionné si on est sur la vue prêts
        preselected_id = None
        if self.stack.currentWidget() is self.loan_list_view:
            preselected_id = self.loan_list_view.get_selected_loan_id()

        # Ouvrir le dialogue (comme le clic droit)
        dlg = ReturnLoanDialog(self, preselected_loan_id=preselected_id)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_loan_id:
            from .services.loan_service import return_loan as service_return

            service_return(dlg.selected_loan_id)
            self.dataChanged.emit()

    @Slot(int)
    def return_loan_by_id(self, loan_id: int):
        """Retourne un emprunt par son ID (appelé par signal double-clic)."""
        # Juste ouvrir le dialogue avec cet ID
        dlg = ReturnLoanDialog(self, preselected_loan_id=loan_id)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_loan_id:
            from .services.loan_service import return_loan as service_return

            service_return(dlg.selected_loan_id)
            self.dataChanged.emit()

    @Slot()
    def import_books(self):
        """Ouvre le dialogue d'import."""
        dlg = ImportDialog(self, self.prefs)
        if dlg.exec():
            # 🔧 FIX : Appeler refresh ET émettre le signal
            self.refresh_all_views()
            self.dataChanged.emit()

    @Slot()
    def open_preferences(self):  # ← Remove underscore
        """Ouvre le dialogue des préférences."""
        dlg = PreferencesDialog(self, prefs=self.prefs)  # ← Fix attribute name
        if dlg.exec():
            if dlg.result:  # ← Check result exists
                self.prefs = dlg.result  # ← Fix attribute name
                save_preferences(self.prefs)

                # Appliquer le thème immédiatement
                self.apply_theme(self.prefs.theme)

                QMessageBox.information(
                    self, translate("preferences.title"), translate("preferences.saved_body")
                )

    @Slot()
    def about(self):
        QMessageBox.about(self, translate("about.title"), translate("about.body"))

    def apply_theme(self, theme_name: str) -> None:
        """Applique un thème et recharge les icônes.

        Cette méthode est appelée quand l'utilisateur change de thème
        dans les préférences.

        Args:
            theme_name: Nom du thème ("dark", "light", "auto")
        """
        try:
            logger.info(f"📱 Changement de thème : {theme_name}")

            # Appliquer le thème qdarktheme
            qdarktheme.setup_theme(theme_name)

            # 🎯 Recharger les icônes avec la nouvelle couleur
            self._reload_icons()

            logger.info(f"✅ Thème '{theme_name}' appliqué avec succès")

        except Exception as e:
            logger.error(f"❌ Erreur lors du changement de thème '{theme_name}': {e}")

    @Slot()
    def online_help(self):
        """Ouvre la page d'aide du projet sur GitHub."""
        url = QUrl("https://github.com/frettbe/Biblio")
        QDesktopServices.openUrl(url)

    def closeEvent(self, event: QCloseEvent):
        """Sauvegarde l'état de la fenêtre avant de quitter."""
        self.book_list_view.save_view_state()
        self.member_list_view.save_view_state()
        self.loan_list_view.save_view_state()

        # Sauvegarder état du splitter
        splitter_state = self.main_splitter.saveState().toBase64().data().decode()
        self.prefs.main_splitter_state = splitter_state

        if self.prefs.remember_window_geometry:
            self.prefs.main_window_geometry = self.saveGeometry()

        save_preferences(self.prefs)
        super().closeEvent(event)

    @Slot()
    def show_about(self):
        """Affiche le dialogue "À propos"."""
        dlg = AboutDialog(self)
        dlg.exec()

    def _reload_icons(self):
        """Recharge toutes les icônes avec la couleur du thème actuel."""
        from .utils.icon_helper import app_icon

        # 🎯 Récupérer le thème actuel
        theme = self.prefs.theme

        logger.info(f"🔄 Rechargement des icônes avec thème : {theme}")

        self.act_new_book.setIcon(toolbar_icon("book-open-text", theme))
        self.act_new_member.setIcon(toolbar_icon("user-plus", theme))
        self.act_new_loan.setIcon(toolbar_icon("calendar-plus", theme))
        self.act_import.setIcon(toolbar_icon("download-simple", theme))
        self.act_import_members.setIcon(toolbar_icon("file-arrow-up", theme))
        self.act_export.setIcon(toolbar_icon("upload-simple", theme))
        self.act_search.setIcon(toolbar_icon("magnifying-glass", theme))
        self.act_edit_item.setIcon(toolbar_icon("pencil-simple", theme))
        self.act_delete_item.setIcon(toolbar_icon("trash", theme))
        self.act_preferences.setIcon(toolbar_icon("gear", theme))
        self.act_about.setIcon(toolbar_icon("info", theme))

        # Actions du menu
        if hasattr(self, "act_refresh"):
            self.act_refresh.setIcon(toolbar_icon("arrow-clockwise", theme))
        if hasattr(self, "act_quit"):
            self.act_quit.setIcon(toolbar_icon("x", theme))
        if hasattr(self, "act_docs"):
            self.act_docs.setIcon(toolbar_icon("question", theme))
        if hasattr(self, "act_show_dashboard"):
            self.act_show_dashboard.setIcon(toolbar_icon("chart-pie", theme))
        if hasattr(self, "act_show_books"):
            self.act_show_books.setIcon(toolbar_icon("books", theme))
        if hasattr(self, "act_show_members"):
            self.act_show_members.setIcon(toolbar_icon("users", theme))
        if hasattr(self, "act_show_loans"):
            self.act_show_loans.setIcon(toolbar_icon("hand-coins", theme))
        if hasattr(self, "act_show_split"):
            self.act_show_split.setIcon(toolbar_icon("columns", theme))
        if hasattr(self, "act_return_loan"):
            self.act_return_loan.setIcon(toolbar_icon("arrow-u-up-left", theme))

        # Icône application
        self.setWindowIcon(app_icon("sun-horizon", theme))

        logger.info("✅ Icônes rechargées")

    @Slot(str, bool)
    def _on_filter_loans_from_dashboard(self, filter_label: str, overdue_only: bool):
        """
        Affiche la liste des prêts avec un filtre appliqué.

        Args:
            filter_label: Libellé du filtre (non utilisé pour l'instant)
            overdue_only: True si on veut afficher seulement les retards
        """
        # Passer à la vue des prêts
        self.show_loan_list()

        # Appliquer le filtre correspondant
        if overdue_only:
            # Filtrer sur les retards
            if hasattr(self.loan_list_view, "filter_overdue"):
                self.loan_list_view.filter_overdue()
        else:
            # Afficher tous les prêts ouverts (pas de filtre supplémentaire)
            if hasattr(self.loan_list_view, "clear_filters"):
                self.loan_list_view.clear_filters()  # Optionnel si tu as cette méthode

    @Slot()
    def export_current_view(self):
        """Exporte les données de la vue courante."""
        current_widget = self.stack.currentWidget()

        # Déterminer quelle vue est active
        if current_widget == self.book_list_view:
            self.book_list_view._on_export()
        elif current_widget == self.member_list_view:
            self.member_list_view._on_export()
        elif current_widget == self.loan_list_view:
            # 🔥 Loan list n'a pas encore d'export, à implémenter
            self.loan_list_view._on_export()
        elif current_widget == self.splitter:
            # Export de la split view : on peut demander à l'utilisateur
            self._export_split_view()
        else:
            # Dashboard ou autre vue sans export
            QMessageBox.information(
                self,
                translate("export.not_available_title"),
                translate("export.not_available_body"),
            )

    def _export_split_view(self):
        """Demande à l'utilisateur quelle vue exporter dans la split view."""
        from PySide6.QtWidgets import QMessageBox

        # Créer une QMessageBox personnalisée
        msgbox = QMessageBox(self)
        msgbox.setWindowTitle(translate("export.split_choice_title"))
        msgbox.setText(translate("export.split_choice_body"))
        msgbox.setIcon(QMessageBox.Icon.Question)

        # Créer des boutons personnalisés
        btn_books = msgbox.addButton(
            translate("export.split_button_books"), QMessageBox.ButtonRole.YesRole
        )
        btn_members = msgbox.addButton(
            translate("export.split_button_members"), QMessageBox.ButtonRole.NoRole
        )
        btn_cancel = msgbox.addButton(
            translate("export.split_button_cancel"), QMessageBox.ButtonRole.RejectRole
        )

        msgbox.setDefaultButton(btn_cancel)

        # Afficher et récupérer le bouton cliqué
        msgbox.exec()
        clicked = msgbox.clickedButton()

        if clicked == btn_books:
            self.book_list_split._on_export()
        elif clicked == btn_members:
            self.member_list_split._on_export()
        # Si cancel ou fermeture, on ne fait rien

    @Slot(int)
    def _on_view_changed(self, index: int) -> None:
        """Adapte le panneau détails selon la vue active.

        Args:
            index: Index de la vue active dans self.stack.
        """
        # Index: 0=Dashboard, 1=Books, 2=Members, 3=Loans, 4=Split
        if index == 1:  # Vue Livres
            self.details_stack.setCurrentWidget(self.book_details_panel)
            self.book_details_panel.clear()
        elif index == 2:  # Vue Membres
            self.details_stack.setCurrentWidget(self.member_details_panel)
            self.member_details_panel.clear()

    @Slot(Member)
    def _on_member_row_selected(self, member: Member) -> None:
        """Met à jour le panneau détails quand un membre est sélectionné."""
        if member:
            self.member_details_panel.update_from_member(member)

    def _connect_selection_signals(self):
        """Connecte les signaux de sélection après chargement des vues."""
        try:
            # Vues simples (déjà connectées)
            self.book_list_view.table_view.selectionModel().selectionChanged.connect(
                self._on_book_selection_changed
            )
            self.member_list_view.table_view.selectionModel().selectionChanged.connect(
                self._on_member_selection_changed
            )

            self.book_list_split.table_view.selectionModel().selectionChanged.connect(
                self._on_book_split_selection_changed
            )
            self.member_list_split.table_view.selectionModel().selectionChanged.connect(
                self._on_member_split_selection_changed
            )

            print("✅ Signaux de sélection connectés avec succès (vues simples + split)")
        except Exception as e:
            print(f"❌ Erreur connexion signaux: {e}")

    @Slot()
    def _on_book_selection_changed(self) -> None:
        """Met à jour le panneau détails quand un livre est sélectionné."""

        selected_rows = self.book_list_view.table_view.selectionModel().selectedRows()

        if not selected_rows:
            self.book_details_panel.clear()
            return

        # Mapper vers le modèle source (en cas de proxy)
        proxy_index = selected_rows[0]
        source_index = self.book_list_view.proxy_model.mapToSource(proxy_index)

        # Récupérer le livre
        book = self.book_list_view.table_model.get_book_by_row(source_index.row())

        if book:
            self.book_details_panel.update_from_book(book)

    @Slot()
    def _on_member_selection_changed(self) -> None:
        """Met à jour le panneau détails quand un membre est sélectionné."""

        selected_rows = self.member_list_view.table_view.selectionModel().selectedRows()

        if not selected_rows:
            self.member_details_panel.clear()
            return

        # Mapper vers le modèle source (en cas de proxy)
        proxy_index = selected_rows[0]
        source_index = self.member_list_view.proxy_model.mapToSource(proxy_index)

        # Récupérer le membre
        member = self.member_list_view.table_model.get_member_by_row(source_index.row())

        if member:
            self.member_details_panel.update_from_member(member)

    @Slot()
    def _on_book_split_selection_changed(self) -> None:
        """Met à jour le panneau détails quand un livre est sélectionné dans la split view."""
        # 🎯 NOUVEAU : Basculer vers le panneau livres
        self.details_stack.setCurrentWidget(self.book_details_panel)

        selected_rows = self.book_list_split.table_view.selectionModel().selectedRows()

        if not selected_rows:
            self.book_details_panel.clear()
            return

        # Mapper vers le modèle source
        proxy_index = selected_rows[0]
        source_index = self.book_list_split.proxy_model.mapToSource(proxy_index)

        # Récupérer le livre
        book = self.book_list_split.table_model.get_book_by_row(source_index.row())

        if book:
            self.book_details_panel.update_from_book(book)

    @Slot()
    def _on_member_split_selection_changed(self) -> None:
        """Met à jour le panneau détails quand un membre est sélectionné dans la split view."""
        # 🎯 NOUVEAU : Basculer vers le panneau membres
        self.details_stack.setCurrentWidget(self.member_details_panel)

        selected_rows = self.member_list_split.table_view.selectionModel().selectedRows()

        if not selected_rows:
            self.member_details_panel.clear()
            return

        # Mapper vers le modèle source
        proxy_index = selected_rows[0]
        source_index = self.member_list_split.proxy_model.mapToSource(proxy_index)

        # Récupérer le membre
        member = self.member_list_split.table_model.get_member_by_row(source_index.row())

        if member:
            self.member_details_panel.update_from_member(member)


def main():
    """Point d'entrée de l'application."""
    QCoreApplication.setOrganizationName("6f4")
    QCoreApplication.setApplicationName("Aurora")
    ensure_tables()

    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
