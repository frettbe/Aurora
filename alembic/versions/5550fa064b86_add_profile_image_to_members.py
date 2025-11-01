"""add_profile_image_to_members

Revision ID: 5550fa064b86
Revises: 61bf77348251
Create Date: 2025-11-01 14:07:47.294844

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5550fa064b86"
down_revision: str | None = "61bf77348251"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Ajoute le champ profile_image à la table members.
    Stocke le chemin vers la photo de profil du membre.
    """
    op.add_column("members", sa.Column("profile_image", sa.String(length=500), nullable=True))


def downgrade() -> None:
    """
    Supprime le champ profile_image de la table members.
    """
    op.drop_column("members", "profile_image")
