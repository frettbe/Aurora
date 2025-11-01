#!/usr/bin/env python3
"""
Hook pre-commit pour générer automatiquement le Project Map Aurora-Community.
Génère le fichier dans le dossier parent (D:/prog/).
"""

import subprocess
import sys
from pathlib import Path


def generate_project_map():
    """Génère le Project Map Aurora-Community."""
    # Chemin vers le repo Aurora-Community
    repo_root = Path(__file__).parent.parent

    # Chemin vers le dossier parent (D:\prog\)
    parent_dir = repo_root.parent

    # Chemin vers le script générateur
    mapper_script = parent_dir / "project_mapper_qwenCoder_rev.py"

    # Chemin de sortie
    output_file = parent_dir / "AuroraCommunity.md"

    # Commande exacte que tu utilises
    cmd = ["python", str(mapper_script), "--project", str(repo_root), "--output", str(output_file)]

    try:
        print("[INFO] Generation du Project Map Aurora-Community en cours...")
        subprocess.run(
            cmd,
            cwd=parent_dir,
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            errors="replace",
        )
        print(f"[OK] Project Map genere : {output_file}")
        print("[!] Pensez a l'uploader dans l'espace Perplexity !")
        return 0
    except subprocess.CalledProcessError as e:
        print("[ERREUR] Echec de la generation du Project Map:")
        print(e.stderr)
        return 1
    except FileNotFoundError:
        print(f"[ERREUR] Script non trouve : {mapper_script}")
        return 1


if __name__ == "__main__":
    sys.exit(generate_project_map())
