from libapp.services.import_service import clean_authors


def test_clean_authors():
    assert clean_authors("Victor Hugo (Auteur du texte)") == "Victor Hugo"
    assert clean_authors("Doe, John; Jane Doe | Jack & Jill") == "Doe, John, Jane Doe, Jack, Jill"
    assert clean_authors(None) is None
