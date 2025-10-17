import sys

import pandas as pd


def test_import_without_isbn(tmp_path, monkeypatch):
    """
    Vérifie que l'import accepte un XLSX avec titre présent et ISBN absent,
    et que le nettoyage d'auteurs est appliqué (sans appel réseau).
    """
    # Isoler DB dans un fichier temporaire
    db_file = tmp_path / "biblio_test.db"
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + str(db_file).replace("\\", "/"))

    # Recharger modules DB si besoin (important après env)
    for mod in [
        "libapp.utils.paths",
        "libapp.persistence.base",
        "libapp.persistence.models_sa",
        "libapp.persistence.database",
        "libapp.services.import_service",
    ]:
        if mod in sys.modules:
            del sys.modules[mod]

    from libapp.persistence.database import ensure_tables, get_session
    from libapp.persistence.models_sa import Book
    from libapp.services.import_service import ImportService  # si c'est une classe

    # Si dans ton projet c'est une fonction module-level:
    # from libapp.services.import_service import import_books_advanced as do_import

    ensure_tables()

    # 1) Crée un XLSX minimal (ISBN vide)
    xlsx_path = tmp_path / "import_test.xlsx"
    df = pd.DataFrame(
        [
            {
                "Titre": "Les Misérables",
                "Auteur": "Victor Hugo (Auteur du texte)",
                "ISBN": "",
                "Éditeur": "Aucune",
                "Année": "1862",
            }
        ]
    )
    df.to_excel(xlsx_path, index=False)

    # 2) Mapping Excel -> champs internes attendus par ton import
    mapping = {
        "title": "Titre",
        "author": "Auteur",
        "isbn": "ISBN",
        "publisher": "Éditeur",
        "year": "Année",
    }

    # 3) Appel sans enrichissement réseau
    svc = ImportService()
    result, errors = svc.import_books_advanced(
        file_path=str(xlsx_path),
        user_mapping=mapping,
        use_bnf=False,  # ← pas d'appel réseau en CI
        fallback_title_author=False,  # ← idem
        policy="merge",
        bnf=None,
    )

    # 4) Assertions basiques
    assert errors == []
    # selon ta structure d'ImportResult; adapte au besoin (ex: result.created)
    created_count = getattr(result, "created", None) or getattr(result, "count", None)
    if created_count is None:
        # fallback: compte en base
        with get_session() as s:
            created_count = s.query(Book).count()
    assert created_count >= 1

    # 5) Vérifie le nettoyage d'auteurs
    with get_session() as s:
        b = s.query(Book).filter(Book.title == "Les Misérables").first()
        assert b is not None
        assert (b.author or "").strip() == "Victor Hugo"
