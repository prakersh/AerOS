"""add line_item_ids_json to rfxvendor

Revision ID: a1b2c3d4e5f6
Revises: 5dcda45063d9
Create Date: 2026-05-28 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '5dcda45063d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('rfxvendor', sa.Column('line_item_ids_json', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('rfxvendor', 'line_item_ids_json')
