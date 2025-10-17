"""Tests des règles métier pour les prêts."""

from __future__ import annotations

import sys

import pytest
from sqlalchemy import delete


def test_no_double_open_loan(tmp_path, monkeypatch):
    """Vérifie qu'on ne peut pas créer deux prêts ouverts pour le même couple livre/membre."""
    # Isoler les répertoires (DB/prefs) et la DB
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))

    db_file = tmp_path / "biblio_test.db"
    db_url = "sqlite:///" + str(db_file).replace("\\", "/")
    monkeypatch.setenv("DATABASE_URL", db_url)

    from libapp.persistence.database import ensure_tables, get_session
    from libapp.persistence.models_sa import Book, Loan, Member
    from libapp.services.loan_service import LoanError, create_loan, return_loan

    # Recharger modules (pour prendre l'URL ci-dessus)
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

    # DB propre
    with get_session() as s:
        s.execute(delete(Loan))
        s.commit()

    # Seed
    with get_session() as s:
        b = Book(title="Test Book", copies_total=3, copies_available=3)
        m = Member(member_no="TST-002", first_name="Bob", last_name="User")
        s.add_all([b, m])
        s.commit()
        bid, mid = b.id, m.id

    # 1er prêt OK
    loan1 = create_loan(book_id=bid, member_id=mid)

    # 2e prêt (même couple) doit échouer tant que le 1er n'est pas rendu
    with pytest.raises(LoanError):
        create_loan(book_id=bid, member_id=mid)

    # Retour du 1er prêt
    return_loan(loan1.id)

    # Après retour, un nouveau prêt redevient possible
    loan2 = create_loan(book_id=bid, member_id=mid)
    assert loan2.id is not None
