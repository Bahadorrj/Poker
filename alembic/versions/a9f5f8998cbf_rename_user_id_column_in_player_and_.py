"""Rename user_id column in Player and GameTable to owner_id

Revision ID: a9f5f8998cbf
Revises: c9385c7d80ab
Create Date: 2026-04-28 20:14:36.534669

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a9f5f8998cbf"
down_revision: Union[str, Sequence[str], None] = "c9385c7d80ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    with op.batch_alter_table("game_tables") as batch_op:
        batch_op.alter_column("user_id", new_column_name="owner_id")


def downgrade():
    with op.batch_alter_table("game_tables") as batch_op:
        batch_op.alter_column("owner_id", new_column_name="user_id")
