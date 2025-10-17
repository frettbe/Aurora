"""
Service pour interroger l'API OpenLibrary.

Recherche des informations sur un livre par ISBN et les transforme
en `BookDTO` via son adaptateur.
"""

from __future__ import annotations

from dataclasses import dataclass

import requests

from .utils import clean_author, normalize_isbn


@dataclass
class ExtBook:
    titre: str
    sous_titre: str | None
    auteurs: list[str]
    isbn: str | None
    editeur: str | None
    date_publication: str | None
    collection: str | None


class OpenLibraryService:
    BASE = "https://openlibrary.org"

    def search_by_isbn(self, isbn: str) -> ExtBook | None:
        """Recherche par ISBN - inchangée, fonctionne déjà."""
        s = normalize_isbn(isbn)
        if not s:
            return None
        url = f"{self.BASE}/isbn/{s}.json"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code != 200:
                return None
            data = r.json()
            return self._map(data)
        except Exception:
            return None

    def search_by_title(self, title: str) -> list[ExtBook]:
        """Recherche par titre avec récupération des éditions détaillées.

        Utilise l'approche works → editions pour récupérer les ISBN et éditeurs.

        Args:
            title: Titre du livre à rechercher

        Returns:
            Liste d'ExtBook avec ISBN et éditeur remplis
        """
        url = f"{self.BASE}/search.json"
        try:
            # Première requête pour obtenir les works
            r = requests.get(url, params={"title": title, "limit": 3}, timeout=10)

            if r.status_code != 200:
                return []

            docs = r.json().get("docs", [])
            results = []

            for doc in docs:
                work_key = doc.get("key")
                if not work_key:
                    continue

                # Récupérer les éditions pour ce work
                editions_url = f"{self.BASE}{work_key}/editions.json"
                try:
                    editions_response = requests.get(editions_url, timeout=10)

                    if editions_response.status_code == 200:
                        editions_data = editions_response.json()
                        entries = editions_data.get("entries", [])

                        # Prendre la première édition avec les meilleures données
                        for edition in entries[:3]:  # Max 3 éditions par work
                            ext_book = self._map_edition(edition, doc)
                            if ext_book:
                                results.append(ext_book)
                                break  # Une seule édition par work pour éviter doublons

                except Exception:
                    # Si on ne peut pas récupérer les éditions, on utilise les données de base
                    basic_book = self._map(doc)
                    if basic_book:
                        results.append(basic_book)

            return results

        except Exception:
            return []

    def _map_edition(self, edition_data: dict, work_data: dict) -> ExtBook | None:
        """Mappe les données d'édition + work vers ExtBook.

        Args:
            edition_data: Données de l'édition (avec ISBN, éditeur, etc.)
            work_data: Données du work (avec titre, auteur de base)

        Returns:
            ExtBook avec toutes les données disponibles
        """
        if not edition_data:
            return None

        # Priorité au titre de l'édition, sinon titre du work
        title = edition_data.get("title") or work_data.get("title")
        if not title:
            return None

        # Récupération des auteurs depuis le work (plus fiable)
        auteurs = []
        for author_name in work_data.get("author_name", []):
            if author_name:
                auteurs.append(clean_author(str(author_name)))

        # Gestion ISBN avec correction de la notation scientifique
        isbn = None
        for isbn_field in ["isbn_13", "isbn_10"]:
            isbn_list = edition_data.get(isbn_field, [])
            if isinstance(isbn_list, list) and isbn_list:
                isbn_raw = str(isbn_list[0])
                # Correction notation scientifique (ex: 9.782213636733e+12)
                if "e+" in isbn_raw.lower():
                    try:
                        isbn = str(int(float(isbn_raw)))
                    except (ValueError, OverflowError):
                        isbn = isbn_raw
                else:
                    isbn = isbn_raw

                isbn = normalize_isbn(isbn)
                if isbn:  # Si normalize_isbn réussit, on garde
                    break

        # Gestion éditeur
        publishers = edition_data.get("publishers", [])
        editeur = None
        if isinstance(publishers, list) and publishers:
            editeur = str(publishers[0])

        # Date de publication - priorité à l'édition
        date_pub = edition_data.get("publish_date")
        if not date_pub:
            first_year = work_data.get("first_publish_year")
            if first_year:
                date_pub = str(first_year)

        return ExtBook(
            titre=title,
            sous_titre=edition_data.get("subtitle"),
            auteurs=auteurs,
            isbn=isbn,
            editeur=editeur,
            date_publication=date_pub,
            collection=None,
        )

    def _map(self, d: dict) -> ExtBook | None:
        """Convertit les données brutes OpenLibrary vers ExtBook.

        Version basique pour les données sans édition détaillée.
        """
        if not d:
            return None

        titre = d.get("title")
        if not titre:
            return None

        # Gestion sécurisée des auteurs
        auteurs = []
        for a in d.get("authors", []) or d.get("author_name", []):
            if isinstance(a, dict):
                name = a.get("name")
            else:
                name = str(a)
            if name:
                auteurs.append(clean_author(name))

        # Gestion sécurisée de l'ISBN
        isbn_data = d.get("isbn")
        if isinstance(isbn_data, list) and isbn_data:
            isbn = normalize_isbn(isbn_data[0])
        elif isbn_data:
            isbn = normalize_isbn(str(isbn_data))
        else:
            isbn = None

        # Gestion sécurisée de l'éditeur
        pub_data = d.get("publishers")
        if isinstance(pub_data, list) and pub_data:
            editeur = str(pub_data[0])
        else:
            editeur = d.get("publisher")
            if editeur:
                editeur = str(editeur)

        # Gestion de la date de publication
        date_pub = None
        if "publish_date" in d:
            date_pub = d.get("publish_date")
        elif "first_publish_year" in d:
            date_pub = str(d.get("first_publish_year"))

        return ExtBook(
            titre=titre,
            sous_titre=d.get("subtitle"),
            auteurs=auteurs,
            isbn=isbn,
            editeur=editeur,
            date_publication=date_pub,
            collection=None,
        )
