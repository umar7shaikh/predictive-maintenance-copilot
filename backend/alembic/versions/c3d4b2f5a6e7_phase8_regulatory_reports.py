"""phase 8 — regulatory reports

Revision ID: c3d4b2f5a6e7
Revises: d4e5c3a6b7f8
Create Date: 2026-06-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4b2f5a6e7'
down_revision: Union[str, None] = 'd4e5c3a6b7f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'regulatory_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('framework', sa.String(length=16), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('region', sa.String(length=32), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_regulatory_reports_framework'), 'regulatory_reports', ['framework'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_regulatory_reports_framework'), table_name='regulatory_reports')
    op.drop_table('regulatory_reports')
