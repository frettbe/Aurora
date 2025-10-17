from __future__ import annotations

from sqlalchemy import func, inspect
from sqlalchemy.exc import OperationalError

from libapp.persistence.database import SessionLocal
from libapp.persistence.models_sa import Author, Book


# [PATCH-START get_suggestions search_index.py]
def get_suggestions(limit=200):
    """
    Renvoie (titles, authors). Au premier lancement (DB vierge), si les tables
    ne sont pas encore visibles, on renvoie des listes vides plutôt que d'échouer.
    """
    with SessionLocal() as s:
        insp = inspect(s.bind)
        try:
            has_books = insp.has_table("books")
            has_authors = insp.has_table("authors")
        except Exception:
            # si l’inspecteur échoue (backend exotique), on reste prudent
            has_books = False
            has_authors = False

        if not (has_books and has_authors):
            return [], []

        try:
            titles = (
                s.query(Book.title)
                .filter(Book.title.isnot(None))
                .filter(func.trim(Book.title) != "")
                .group_by(func.trim(Book.title))
                .order_by(func.trim(Book.title).asc())
                .limit(limit)
                .all()
            )
            authors = (
                s.query(Author.name)
                .filter(Author.name.isnot(None))
                .filter(func.trim(Author.name) != "")
                .group_by(func.trim(Author.name))
                .order_by(func.trim(Author.name).asc())
                .limit(limit)
                .all()
            )
            return [t[0] for t in titles], [a[0] for a in authors]
        except OperationalError:
            # ex: la table a été supprimée entre-temps
            return [], []


# [PATCH-END get_suggestions search_index.py]
