import os
import sys
import uuid

import pytest

# Ajoute la racine du dépôt (celle qui contient libapp/) au PYTHONPATH
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    # Env
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))
    db_file = tmp_path / f"biblio_{uuid.uuid4().hex}.db"
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + str(db_file).replace("\\", "/"))
    # Reload
    for mod in [
        "libapp.utils.paths",
        "libapp.persistence.base",
        "libapp.persistence.models_sa",
        "libapp.persistence.database",
        "libapp.services.loan_service",
    ]:
        sys.modules.pop(mod, None)
    yield
