from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import requests

SRU = "https://catalogue.bnf.fr/api/SRU"
SCHEMA = "dublincore"


def _clean_person(s: str) -> str:
    if not s:
        return s
    t = s.strip()

    # 1) retirer les rôles en fin de chaîne (ex: ". Auteur du texte", ". Éditeur scientifique", ". Traducteur", etc.)
    t = re.sub(
        r"\s*\.\s*(auteur(?:\s+du\s+texte)?|éditeur(?:\s+scientifique)?|editeur(?:\s+scientifique)?|"
        r"directeur(?:\s+de\s+publication)?|traducteur|illustrateur|préfacier|postfacier|annotateur)s?\s*$",
        "",
        t,
        flags=re.IGNORECASE,
    )

    # 2) retirer les dates et qualificatifs entre parenthèses en fin de nom : "(1802-1885)", "(19..-....)", "(pseudo-...)", etc.
    t = re.sub(r"\s*\([^)]*\)\s*$", "", t)

    # 3) espaces propres
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t


def _extract_dc_text(elem: ET.Element, tag: str) -> list[str]:
    # les balises dublin core ont souvent le namespace 'dc'
    vals = []
    for n in elem.findall(f".//{{http://purl.org/dc/elements/1.1/}}{tag}"):
        txt = (n.text or "").strip()
        if txt:
            vals.append(txt)
    return vals


def _notice_to_dict(record: ET.Element) -> dict[str, str]:
    md = record.find(".//{http://www.loc.gov/zing/srw/}recordData")
    if md is None:
        return {}
    # champs utiles
    titles = _extract_dc_text(md, "title")
    creators_raw = _extract_dc_text(md, "creator")
    creators = [_clean_person(c) for c in creators_raw if c.strip()]
    publishers = _extract_dc_text(md, "publisher")
    dates = _extract_dc_text(md, "date")
    identifiers = _extract_dc_text(md, "identifier")
    descriptions = _extract_dc_text(md, "description")

    # repérer un ISBN plausible dans 'identifier'
    isbn = ""
    for ident in identifiers:
        t = ident.replace("-", "").replace(" ", "")
        if t.lower().startswith("isbn"):
            t = t[4:].lstrip(":").strip()
        if (10 <= len(t) <= 13) and t.isalnum():
            isbn = t
            break

    return {
        "title": titles[0] if titles else "",
        "author": "; ".join(creators) if creators else "",
        "publisher": publishers[0] if publishers else "",
        "year": (dates[0][:4] if dates and dates[0][:4].isdigit() else ""),
        "isbn": isbn,
        "summary": descriptions[0] if descriptions else "",
    }


class BnfAdapter:
    timeout = 10

    def by_isbn(self, isbn: str) -> dict[str, str] | None:
        if not isbn:
            return None
        q = f'(bib.isbn all "{isbn}")'
        params = {
            "version": "1.2",
            "operation": "searchRetrieve",
            "query": q,
            "recordSchema": SCHEMA,
            "maximumRecords": "5",
        }
        r = requests.get(SRU, params=params, timeout=self.timeout)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        recs = root.findall(".//{http://www.loc.gov/zing/srw/}record")
        if not recs:
            return None
        return _notice_to_dict(recs[0])

    def search_title_author(self, title: str, author: str = "") -> list[dict[str, str]]:
        if not title:
            return []
        # requête SRU : on combine titre et auteur si dispo
        if author:
            q = f'(bib.title all "{title}") and (bib.author all "{author}")'
        else:
            q = f'(bib.title all "{title}")'
        params = {
            "version": "1.2",
            "operation": "searchRetrieve",
            "query": q,
            "recordSchema": SCHEMA,
            "maximumRecords": "20",
        }
        r = requests.get(SRU, params=params, timeout=self.timeout)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        recs = root.findall(".//{http://www.loc.gov/zing/srw/}record")
        out: list[dict[str, str]] = []
        for rec in recs:
            d = _notice_to_dict(rec)
            if any(d.values()):
                out.append(d)
        return out
