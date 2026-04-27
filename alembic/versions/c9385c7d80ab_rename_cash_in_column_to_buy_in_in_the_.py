"""Rename cash_in column to buy_in in the players table

Revision ID: c9385c7d80ab
Revises:
Create Date: 2026-04-27 23:29:39.839147

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c9385c7d80ab"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    with op.batch_alter_table("players") as batch_op:
        batch_op.alter_column("cash_in", new_column_name="buy_in")


def downgrade():
    with op.batch_alter_table("players") as batch_op:
        batch_op.alter_column("buy_in", new_column_name="cash_in")
