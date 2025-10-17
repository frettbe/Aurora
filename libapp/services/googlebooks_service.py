"""
Service pour interroger l'API Google Books.

Ce module fournit les outils pour rechercher des informations sur un livre
via son ISBN en utilisant l'API publique de Google Books. Il est conçu pour
fonctionner avec un adaptateur qui transforme la réponse de l'API en un
objet standardisé (`BookDTO`).
"""

from __future__ import annotations

import logging

import requests

from .types import BookDTO

logger = logging.getLogger("library.services.googlebooks")


class GoogleBooksServiceError(Exception):
    """Exception personnalisée pour les erreurs du service Google Books."""

    pass


class GoogleBooksAdapter:
    """
    Adapte la réponse de l'API Google Books au format `BookDTO`.

    La structure de la réponse de Google Books est complexe et imbriquée.
    Le rôle de cet adaptateur est d'extraire les informations pertinentes
    de manière sûre et de les mapper vers les champs de notre `BookDTO`.
    """

    def __init__(self, item: dict):
        self.item = item
        self.volume_info = item.get("volumeInfo", {})

    def to_book_dto(self) -> BookDTO:
        """Convertit les données de l'API en BookDTO."""
        return BookDTO(
            id=None,
            isbn=self._get_isbn(),
            title=self.volume_info.get("title", ""),
            author=", ".join(self.volume_info.get("authors", [])),
            publisher=self.volume_info.get("publisher"),
            year=self._get_year(),
            # ... d'autres champs pourraient être mappés ici
        )

    def _get_isbn(self) -> str:
        """Recherche un identifiant ISBN-13 dans les données."""
        for identifier in self.volume_info.get("industryIdentifiers", []):
            if identifier.get("type") == "ISBN_13":
                return identifier.get("identifier", "")
        return ""

    def _get_year(self) -> int | None:
        """Extrait l'année de la date de publication."""
        pub_date = self.volume_info.get("publishedDate", "")
        try:
            return int(pub_date[:4])
        except (ValueError, TypeError):
            return None


class GoogleBooksService:
    """Service client pour l'API Google Books."""

    API_URL = "https://www.googleapis.com/books/v1/volumes"

    def __init__(self, timeout: int = 10):
        """
        Initialise le service.

        Args:
            timeout (int): Timeout en secondes pour les requêtes HTTP.
        """
        self.timeout = timeout

    def search_by_isbn(self, isbn: str) -> BookDTO | None:
        """
        Recherche un livre par son ISBN.

        Args:
            isbn (str): L'ISBN à rechercher.

        Returns:
            Un `BookDTO` si un livre est trouvé, sinon `None`.

        Raises:
            GoogleBooksServiceError: En cas de problème de connexion ou d'API.
        """
        params = {"q": f"isbn:{isbn}"}
        try:
            response = requests.get(self.API_URL, params=params, timeout=self.timeout)
            response.raise_for_status()  # Lève une exception pour les codes 4xx/5xx
            data = response.json()

            if data.get("totalItems", 0) > 0:
                item = data["items"][0]
                adapter = GoogleBooksAdapter(item)
                return adapter.to_book_dto()

            return None
        except requests.RequestException as e:
            logger.error("Erreur de connexion à l'API Google Books: %s", e)
            raise GoogleBooksServiceError("Impossible de contacter l'API Google Books.") from e

    def search_by_title_author(self, title: str, author: str = None) -> list[dict]:
        """Recherche par titre et auteur."""
        logger.debug("🔍 GOOGLE BOOKS DEBUG - DÉBUT")
        logger.debug(f"  Titre: '{title}'")
        logger.debug(f"  Auteur: '{author}'")
        try:
            # Construction de la requête Google Books
            query_parts = [f'intitle:"{title}"']
            if author:
                query_parts.append(f'inauthor:"{author}"')

            query = "+".join(query_parts)
            logger.debug(f"  Query construite: '{query}'")

            params = {"q": query, "maxResults": 5, "printType": "books"}
            logger.debug(f"  Params: {params}")

            response = requests.get(self.API_URL, params=params, timeout=self.timeout)
            logger.debug(f"  Status code: {response.status_code}")

            data = response.json()
            logger.debug(f"  Total items dans réponse: {data.get('totalItems', 0)}")

            books = []
            if "items" in data:
                logger.debug(f"  Items trouvés: {len(data['items'])}")
                for i, item in enumerate(data["items"]):
                    logger.debug(
                        f"    Item {i}: {item.get('volumeInfo', {}).get('title', 'No title')}"
                    )
                    if item.get("volumeInfo"):
                        books.append(item)
            else:
                logger.debug("  Aucun 'items' dans la réponse")

            logger.debug(f"  Résultats finaux: {len(books)}")
            return books

        except Exception as e:
            logger.error(f"🚨 GOOGLE BOOKS ERROR: {e}")
            return []
