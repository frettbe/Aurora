"""Tests unitaires pour le service d'export."""

from libapp.services.export_service import ExportMetadata, export_data


def test_export_metadata_generation():
    """Test la génération de métadonnées."""
    metadata = ExportMetadata(
        include_date=True, include_count=True, include_custom_message=False, app_name="Biblio Test"
    )

    lines = metadata.generate_lines(record_count=42)

    assert "Biblio Test" in lines[0]
    assert "42" in lines[2]  # Count


def test_export_csv_basic(tmp_path):
    """Test l'export CSV basique."""
    filepath = tmp_path / "test_export.csv"
    headers = ["ID", "Titre", "Auteur"]
    data = [
        ["1", "Python 101", "John Doe"],
        ["2", "Django", "Jane Smith"],
    ]

    export_data(
        filepath=filepath,
        headers=headers,
        data=data,
        file_format="csv",
        metadata=None,
    )

    assert filepath.exists()
    content = filepath.read_text(encoding="utf-8-sig")
    assert "Python 101" in content
