"""add room planned duration

Revision ID: b3f1d27a9c40
Revises: e9c6184382a3
Create Date: 2026-10-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3f1d27a9c40'
down_revision: Union[str, Sequence[str], None] = 'e9c6184382a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('poker_rooms', sa.Column('planned_duration_hours', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('poker_rooms', 'planned_duration_hours')
