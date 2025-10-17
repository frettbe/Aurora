from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QMenu, QWidget

from ..services.translation_service import translate


class ContextMenuMixin(QWidget):
    """Ajoute un menu contextuel simple basé sur une liste (label, slot)."""

    def _popup_context(self, pos, actions: list[tuple[str, Callable[[], None]]]) -> None:
        menu = QMenu(self)
        for key, slot in actions:
            act = menu.addAction(translate(key))
            act.triggered.connect(slot)
        menu.exec(self.viewport().mapToGlobal(pos))
