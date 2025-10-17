"""
Service pour interroger le catalogue de la BNF via son API SRU.

Ce service recherche des notices de livres par ISBN et utilise un adaptateur
pour convertir les données XML complexes en un `BookDTO` standard.
"""

from __future__ import annotations

import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from .utils import clean_author, normalize_isbn


@dataclass
class BnfBook:
    titre: str
    sous_titre: str | None
    auteurs: list[str]
    isbn: str | None
    editeur: str | None
    date_publication: str | None
    collection: str | None


class BnfService:
    """
    Client SRU minimal pour la BnF : https://catalogue.bnf.fr/api/SRU

    - Recherche par ISBN (prioritaire si dispo)
    - Recherche par titre+auteur (fallback pour l'étape 6)

    Sortie normalisée -> BnfBook
    """

    BASE = "https://catalogue.bnf.fr/api/SRU"

    def __init__(self, *, timeout: float = 10.0, maximum_records: int = 3):
        self.timeout = timeout
        self.maximum_records = str(max(1, min(10, maximum_records)))

    def search_by_isbn(self, isbn: str) -> BnfBook | None:
        """Recherche BnF par ISBN."""
        normalized_isbn = normalize_isbn(isbn)
        if not normalized_isbn:
            return None

        # Correction notation scientifique si nécessaire
        if "e+" in str(normalized_isbn).lower():
            try:
                normalized_isbn = str(int(float(normalized_isbn)))
            except (ValueError, OverflowError):
                pass

        query = f'(bib.isbn_any all "{normalized_isbn}")'
        return self._search_sru(query)

    def search_by_title_author(self, title: str, author: str | None = None) -> list[BnfBook]:
        """Recherche BnF par titre et auteur (optionnel)."""
        if not title:
            return []

        parts = [f'(bib.title all "{title}")']
        if author:
            parts.append(f'(bib.author all "{author}")')

        query = " and ".join(parts)
        result = self._search_sru(query)
        return [result] if result else []

    def _search_sru(self, query: str) -> BnfBook | None:
        """Exécute une recherche SRU et parse le premier résultat."""
        params = {
            "version": "1.2",
            "operation": "searchRetrieve",
            "recordSchema": "intermarcXchange",
            "maximumRecords": self.maximum_records,
            "query": query,
        }

        url = f"{self.BASE}?{urllib.parse.urlencode(params)}"

        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "Mozilla/5.0 (compatible; BibApp/1.0)")

            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                content = response.read()

            # Parser la réponse SRU
            root = ET.fromstring(content)
            ns = {"srw": "http://www.loc.gov/zing/srw/"}

            # Vérifier les erreurs
            diagnostics = root.findall(".//{http://www.loc.gov/zing/srw/diagnostic/}diagnostic")
            if diagnostics:
                return None

            # Extraire les records
            records = root.findall(".//srw:record", ns)
            if not records:
                return None

            # Parser le premier record
            first_record = records[0]
            record_raw = ET.tostring(first_record, encoding="unicode")

            return self._parse_intermarc(record_raw)

        except Exception:
            return None

    def _parse_intermarc(self, record_raw: str) -> BnfBook | None:
        """Parse une notice INTERMARC en BnfBook.

        Utilise les namespaces XML correctement pour extraire les champs MARC.
        """
        try:
            container = ET.fromstring(f"<container>{record_raw}</container>")

            # 🎯 Namespace MARC XML
            ns = {"ns1": "info:lc/xmlns/marcxchange-v2"}

            def first_text(codes: list[str]) -> str | None:
                """Trouve le premier texte non vide parmi les codes MARC."""
                for code in codes:
                    if "$" not in code:
                        continue

                    tag, sub = code.split("$", 1)
                    xpath = f".//ns1:datafield[@tag='{tag}']/ns1:subfield[@code='{sub}']"
                    el = container.find(xpath, ns)

                    if el is not None:
                        val = (el.text or "").strip()
                        if val:
                            return val
                return None

            def all_texts(codes: list[str]) -> list[str]:
                """Trouve tous les textes pour les codes donnés."""
                results = []
                for code in codes:
                    if "$" not in code:
                        continue

                    tag, sub = code.split("$", 1)
                    xpath = f".//ns1:datafield[@tag='{tag}']/ns1:subfield[@code='{sub}']"
                    elements = container.findall(xpath, ns)

                    for el in elements:
                        val = (el.text or "").strip()
                        if val:
                            results.append(clean_author(val))
                return results

            # 🎯 Extraction des champs principaux
            titre = first_text(["245$a"])
            if not titre:
                return None

            sous_titre = first_text(["245$e", "245$b"])

            # Auteurs depuis différents champs possibles
            auteurs = []
            auteurs.extend(all_texts(["245$f"]))  # Auteur dans le titre
            auteurs.extend(all_texts(["100$a", "100$m"]))  # Auteur principal
            auteurs.extend(all_texts(["700$a", "700$m"]))  # Auteurs secondaires

            # Dédoublonnage des auteurs
            auteurs_uniques = []
            for auteur in auteurs:
                if auteur and auteur not in auteurs_uniques:
                    auteurs_uniques.append(auteur)

            # ISBN - gestion multiple formats
            isbn = first_text(["020$a", "021$a"])
            if isbn:
                # Nettoyer l'ISBN (enlever les mentions comme "rel.", "br.")
                isbn = isbn.split()[0] if " " in isbn else isbn
                isbn = normalize_isbn(isbn)

                # Correction notation scientifique BnF
                if isbn and "e+" in str(isbn).lower():
                    try:
                        isbn = str(int(float(isbn)))
                    except (ValueError, OverflowError):
                        pass

            # Éditeur
            editeur = first_text(["260$c", "264$b"])

            # Date de publication
            date_pub = first_text(["260$d", "264$c"])
            if date_pub:
                # Extraire juste l'année (nettoyer "impr. 2010" → "2010")
                import re

                match = re.search(r"(\d{4})", date_pub)
                if match:
                    date_pub = match.group(1)

            return BnfBook(
                titre=titre,
                sous_titre=sous_titre,
                auteurs=auteurs_uniques,
                isbn=isbn,
                editeur=editeur,
                date_publication=date_pub,
                collection=None,  # BnF ne fournit pas ce champ de manière fiable
            )

        except Exception:
            return None
