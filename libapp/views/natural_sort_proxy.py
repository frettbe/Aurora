"""Proxy model pour le tri naturel des colonnes alphanumériques.

Ce module fournit un QSortFilterProxyModel personnalisé qui effectue
un tri naturel (humain) plutôt qu'un tri lexicographique.
"""

from __future__ import annotations

import re

from PySide6.QtCore import QModelIndex, QSortFilterProxyModel


class NaturalSortProxyModel(QSortFilterProxyModel):
    """Proxy model avec tri naturel pour les valeurs alphanumériques.

    Permet de trier les strings contenant des nombres de façon intuitive :
    - Tri lexicographique : "1", "10", "100", "2" ❌
    - Tri naturel : "1", "2", "10", "100" ✅
    """

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        """Compare deux valeurs en utilisant le tri naturel.

        Args:
            left: Index du premier élément.
            right: Index du deuxième élément.

        Returns:
            True si left < right selon le tri naturel.
        """
        left_data = self.sourceModel().data(left)
        right_data = self.sourceModel().data(right)

        # Si l'une des valeurs est None, utiliser le tri standard
        if left_data is None or right_data is None:
            return super().lessThan(left, right)

        # Convertir en string
        left_str = str(left_data)
        right_str = str(right_data)

        # Appliquer le tri naturel
        return self._natural_sort_key(left_str) < self._natural_sort_key(right_str)

    @staticmethod
    def _natural_sort_key(text: str) -> list[tuple[int, int | str]]:
        """
        Génère une clé de tri naturel pour une string.

        Sépare la string en segments numériques et alphabétiques.
        Les segments numériques sont convertis en int pour un tri correct.
        Chaque segment est transformé en tuple (type, valeur) pour permettre
        la comparaison entre différents types.

        Args:
            text: La string à analyser.

        Returns:
            Liste de tuples (type_indicator, valeur) où type_indicator est :
            - 0 pour les strings (triées en premier)
            - 1 pour les nombres (triés en second)

        Examples:
            >>> _natural_sort_key("A001")
            [(0, 'a'), (1, 1)]
            >>> _natural_sort_key("C 222")
            [(0, 'c '), (1, 222)]
            >>> _natural_sort_key("1984")
            [(1, 1984)]
            >>> _natural_sort_key("Harry Potter")
            [(0, 'harry potter')]
        """
        # Séparer les parties numériques et non-numériques
        # Regex : capture les groupes de chiffres
        parts = re.split(r"(\d+)", text)

        # Convertir en tuples (type, valeur) pour permettre la comparaison
        result = []
        for part in parts:
            if not part:  # Ignorer les strings vides
                continue
            if part.isdigit():
                result.append((1, int(part)))  # Nombres = type 1
            else:
                result.append((0, part.lower()))  # Texte = type 0

        return result
