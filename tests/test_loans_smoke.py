"""Tests smoke pour le flux basique de prêts."""

from __future__ import annotations

import sys

from sqlalchemy import delete


def test_loan_and_return_flow(tmp_path, monkeypatch):
    """Teste le flux complet création + retour d'un prêt."""
    # Isoler les répertoires (DB/prefs) dans un temp dir
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))

    # Isoler la base SQLite par test (fichier dans tmp_path)
    db_file = tmp_path / "biblio_test.db"
    db_url = "sqlite:///" + str(db_file).replace("\\", "/")
    monkeypatch.setenv("DATABASE_URL", db_url)

    from libapp.persistence.database import ensure_tables, get_session
    from libapp.persistence.models_sa import Book, Loan, Member
    from libapp.services.loan_service import create_loan, return_loan

    # Recharger modules DB si besoin (selon ton infra)
    for mod in [
        "libapp.utils.paths",
        "libapp.persistence.base",
        "libapp.persistence.models_sa",
        "libapp.persistence.database",
        "libapp.services.loan_service",
    ]:
        if mod in sys.modules:
            del sys.modules[mod]

    ensure_tables()

    with get_session() as s:
        s.execute(delete(Loan))
        s.commit()

    # Seed minimal
    with get_session() as s:
        b = Book(title="Test Book", copies_total=2, copies_available=2)
        m = Member(member_no="TST-001", first_name="Alice", last_name="Test")
        s.add_all([b, m])
        s.commit()
        bid, mid = b.id, m.id

    # Création prêt (due_date calculée automatiquement)
    loan = create_loan(book_id=bid, member_id=mid)
    assert loan.id is not None

    # Copies dispo décrémentées
    with get_session() as s:
        b2 = s.get(Book, bid)
        assert (b2.copies_available or 0) == 1

    # Retour prêt
    return_loan(loan.id)

    with get_session() as s:
        b3 = s.get(Book, bid)
        ln = s.get(Loan, loan.id)
        assert (b3.copies_available or 0) == 2
        assert ln.return_date is not None
