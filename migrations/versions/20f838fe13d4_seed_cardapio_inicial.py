"""seed cardapio inicial

Revision ID: 20f838fe13d4
Revises: 10724c69c80b
Create Date: 2026-10-15 21:55:58.980417

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20f838fe13d4'
down_revision: Union[str, Sequence[str], None] = '10724c69c80b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

cafes = sa.table("cafes", sa.column("nome", sa.String), sa.column("preco", sa.Numeric))


def upgrade() -> None:
    """Upgrade schema."""
    op.bulk_insert(
        cafes,
        [
            {"nome": "Espresso", "preco": 6.50},
            {"nome": "Cappuccino", "preco": 9.00},
            {"nome": "Latte", "preco": 10.00},
            {"nome": "Mocha", "preco": 11.50},
            {"nome": "Coado Especial", "preco": 8.00},
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "DELETE FROM cafes WHERE nome IN "
        "('Espresso','Cappuccino','Latte','Mocha','Coado Especial')"
    )