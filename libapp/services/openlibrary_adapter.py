from __future__ import annotations

from typing import Any

import requests

BOOKS_API = "https://openlibrary.org/api/books"
ISBN_API = "https://openlibrary.org/isbn/{isbn}.json"
WORKS_API = "https://openlibrary.org{path}.json"


def _year_only(val) -> str:
    s = str(val or "")
    for i, ch in enumerate(s):
        if not ch.isdigit():
            return s[:i]
    return s


class OpenLibraryAdapter:
    def __init__(self, session: requests.Session | None = None, timeout: int = 10):
        self.session = session or requests.Session()
        self.timeout = timeout

    def by_isbn(self, isbn: str) -> dict[str, str] | None:
        isbn = (isbn or "").strip()
        if not isbn:
            return None

        try:
            r = self.session.get(ISBN_API.format(isbn=isbn), timeout=self.timeout)
            if r.status_code == 200:
                b = r.json()
                title = b.get("title") or ""
                author = b.get("by_statement") or ""
                pub = ""
                if isinstance(b.get("publishers"), list) and b["publishers"]:
                    pub = str(b["publishers"][0])
                year = _year_only(b.get("publish_date"))
                if not author and isinstance(b.get("works"), list) and b["works"]:
                    key = b["works"][0].get("key")
                    if key:
                        try:
                            wr = self.session.get(WORKS_API.format(path=key), timeout=self.timeout)
                            if wr.status_code == 200:
                                w = wr.json()
                                names: list[str] = []
                                for a in w.get("authors") or []:
                                    akey = (a.get("author") or {}).get("key")
                                    if akey:
                                        ar = self.session.get(
                                            WORKS_API.format(path=akey), timeout=self.timeout
                                        )
                                        if ar.status_code == 200:
                                            nm = (ar.json() or {}).get("name")
                                            if nm:
                                                names.append(str(nm))
                                if names:
                                    author = ", ".join(names)
                        except Exception:
                            pass
                if any([title, author, pub, year]):
                    return {"title": title, "author": author, "publisher": pub, "year": year}
        except Exception:
            pass

        try:
            params = {"bibkeys": f"ISBN:{isbn}", "jscmd": "data", "format": "json"}
            r = self.session.get(BOOKS_API, params=params, timeout=self.timeout)
            r.raise_for_status()
            data: dict[str, Any] = r.json() or {}
            blob = data.get(f"ISBN:{isbn}") or {}
            if blob:
                title = blob.get("title") or ""
                author = ", ".join(
                    [a.get("name", "") for a in (blob.get("authors") or []) if a.get("name")]
                )
                pub = (
                    (blob.get("publishers") or [{}])[0].get("name", "")
                    if blob.get("publishers")
                    else ""
                )
                year = _year_only(blob.get("publish_date"))
                if any([title, author, pub, year]):
                    return {"title": title, "author": author, "publisher": pub, "year": year}
        except Exception:
            pass
        return None
