"""Helper pour charger les icônes de l'application Aurora."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

# Chemin de base des ressources d'icônes
_ICON_BASE_PATH = Path(__file__).parent.parent / "resources" / "icons"

# 🎯 Variable globale pour stocker le thème actuel
_CURRENT_THEME = "light"


def set_current_theme(theme_name: str) -> None:
    """Définit le thème actuel pour le chargement des icônes.

    Args:
        theme_name: "dark", "light", ou "auto"
    """
    global _CURRENT_THEME
    _CURRENT_THEME = theme_name
    logger.info(f"🎨 Thème enregistré : {theme_name}")


def _get_icon_color(theme_name: str | None = None) -> QColor:
    """Obtient la couleur appropriée pour les icônes selon le thème.

    Args:
        theme_name: "dark", "light", ou "auto". Si None, utilise le thème global.
    """
    if theme_name is None:
        theme_name = _CURRENT_THEME

    if theme_name == "dark":
        color = QColor("#ffffff")  # Blanc en dark
    elif theme_name == "auto":
        # En auto, détecte le thème système
        palette = QApplication.palette()
        window_color = palette.color(palette.ColorRole.Window)
        is_dark = window_color.lightness() < 128
        color = QColor("#ffffff") if is_dark else QColor("#000000")
    else:  # light
        color = QColor("#000000")  # Noir en light

    return color


def load_icon(
    name: str, category: str = "toolbar", size: int = 32, theme: str | None = None
) -> QIcon:
    """Charge une icône SVG et la colore selon le thème.

    Args:
        name: Nom du fichier sans extension
        category: Sous-dossier (toolbar, app, etc.)
        size: Taille en pixels
        theme: Thème à utiliser (None = thème global actuel)

    Returns:
        QIcon colorée selon le thème
    """
    if theme is None:
        theme = _CURRENT_THEME

    icon_path = _ICON_BASE_PATH / category / f"{name}.svg"

    if not icon_path.exists():
        logger.warning(f"⚠️ Icône introuvable : {icon_path}")
        return QIcon()

    # Lire le SVG
    with open(icon_path, encoding="utf-8") as f:
        svg_data = f.read()

    # Obtenir la couleur selon le thème
    color = _get_icon_color(theme)

    # Remplacer currentColor par la couleur du thème
    svg_data = svg_data.replace("currentColor", color.name())

    # Créer le QIcon
    renderer = QSvgRenderer(QByteArray(svg_data.encode()))
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))  # Transparent

    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    return QIcon(pixmap)


def toolbar_icon(name: str, theme: str | None = None) -> QIcon:
    """Charge une icône de toolbar.

    Args:
        name: Nom de l'icône
        theme: Thème à utiliser (None = thème global actuel)
    """
    return load_icon(name, "toolbar", 32, theme)


def app_icon(name: str = "sun-horizon", theme: str | None = None) -> QIcon:
    """Charge une icône d'application.

    Args:
        name: Nom de l'icône
        theme: Thème à utiliser (None = thème global actuel)
    """
    return load_icon(name, "app", 64, theme)
