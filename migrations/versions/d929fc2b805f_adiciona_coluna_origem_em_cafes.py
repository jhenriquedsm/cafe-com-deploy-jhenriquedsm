"""adiciona coluna origem em cafes

Revision ID: d929fc2b805f
Revises: 20f838fe13d4
Create Date: 2026-10-15 22:44:47.527161

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd929fc2b805f'
down_revision: Union[str, Sequence[str], None] = '20f838fe13d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "cafes",
        sa.Column("origem", sa.String(80), nullable=True, server_default="Não informada"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("cafes", "origem")