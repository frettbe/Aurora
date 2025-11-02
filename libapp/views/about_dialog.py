"""
Dialogue "À propos" de l'application.

Affiche les informations sur l'application : version, description,
auteur, licence, technologies utilisées, et liens utiles.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ..services.translation_service import translate
from .__version__ import __app_name__, __license__, __version__


class AboutDialog(QDialog):
    """Dialogue "À propos" affichant les informations de l'application."""

    def __init__(self, parent: QWidget | None = None):
        """Initialise le dialogue "À propos".

        Args:
            parent: Widget parent (généralement MainWindow)
        """
        super().__init__(parent)
        self.setWindowTitle(translate("about.title"))
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        self._setup_ui()

    def _setup_ui(self):
        """Configure l'interface utilisateur."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # === EN-TÊTE : Logo + Titre + Version ===
        header_layout = self._create_header()
        layout.addLayout(header_layout)

        # === SÉPARATEUR ===
        separator = QLabel("═" * 80)
        separator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(separator)

        # === CONTENU : Description + Infos ===
        content = self._create_content()
        layout.addWidget(content)

        # === PIED : Bouton Fermer ===
        footer = self._create_footer()
        layout.addLayout(footer)

        # === STYLE ===
        self.setStyleSheet("""
            AboutDialog {
                background-color: palette(base);
            }
            QLabel#title {
                font-size: 24px;
                font-weight: bold;
                color: palette(highlight);
            }
            QLabel#version {
                font-size: 14px;
                color: palette(mid);
            }
            QTextBrowser {
                border: none;
                background-color: transparent;
            }
        """)

    def _create_header(self) -> QHBoxLayout:
        """Crée l'en-tête avec logo Aurora et titre."""
        from ..utils.icon_helper import app_icon

        header_layout = QHBoxLayout()
        header_layout.setSpacing(20)

        # Logo Aurora
        logo_label = QLabel()
        logo_icon = app_icon()  # Charge sun-horizon.svg

        if not logo_icon.isNull():
            logo_pixmap = logo_icon.pixmap(64, 64)
            logo_label.setPixmap(logo_pixmap)
            header_layout.addWidget(logo_label)

        # Titre + Version
        title_layout = QVBoxLayout()

        title = QLabel(f"🌅 {__app_name__}")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title_layout.addWidget(title)

        version = QLabel(f"Version {__version__}")
        version.setObjectName("version")
        version.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title_layout.addWidget(version)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        return header_layout

    def _create_content(self) -> QTextBrowser:
        """Crée le contenu avec description et informations.

        Returns:
            QTextBrowser contenant le texte formaté
        """
        content = QTextBrowser()
        content.setOpenExternalLinks(True)

        html = f"""
        <html>
        <body style="font-size: 11pt;">

        <h3>{translate("about.description_title")}</h3>
        <p>{translate("about.description_text")}</p>

        <h3>{translate("about.author_title")}</h3>
        <p>
            <b>{translate("about.author_label")}:</b> 6f4<br>
            <b>{translate("about.website_label")}:</b> 
            <a href="https://www.6f4.be">www.6f4.be</a><br>
            <b>{translate("about.email_label")}:</b> 
            <a href="mailto:contact@6f4.be">contact@6f4.be</a>
        </p>

        <h3>{translate("about.license_title")}</h3>
        <p>
            {translate("about.license_text", license=__license__)}<br>
            <small>{translate("about.source_request")}</small>
        </p>

        <!-- ... reste du HTML ... -->

        </body>
        </html>
        """

        content.setHtml(html)
        return content

    def _create_footer(self) -> QHBoxLayout:
        """Crée le pied avec le bouton Fermer.

        Returns:
            Layout horizontal contenant le bouton
        """
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()

        close_button = QPushButton(translate("overdue_alert.close_button"))
        close_button.setMinimumWidth(100)
        close_button.clicked.connect(self.accept)
        footer_layout.addWidget(close_button)

        return footer_layout
