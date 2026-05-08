"""add timestamp mixin

Revision ID: 22dbe15539a2
Revises: a9f5f8998cbf
Create Date: 2026-05-08 12:31:01.184709

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from app.models import now

# revision identifiers, used by Alembic.
revision: str = "22dbe15539a2"
down_revision: Union[str, Sequence[str], None] = "a9f5f8998cbf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Player
    op.add_column("players", sa.Column("created_at", sa.DateTime, default=now))

    # GameTable
    with op.batch_alter_table("game_tables") as batch_op:
        batch_op.alter_column("started_at", new_column_name="created_at")

    # Club
    with op.batch_alter_table("clubs") as batch_op:
        batch_op.alter_column("opened_at", new_column_name="created_at")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("players", "created_at")

    # GameTable
    with op.batch_alter_table("game_tables") as batch_op:
        batch_op.alter_column("created_at", new_column_name="started_at")

    # Club
    with op.batch_alter_table("clubs") as batch_op:
        batch_op.alter_column("created_at", new_column_name="opened_at")
