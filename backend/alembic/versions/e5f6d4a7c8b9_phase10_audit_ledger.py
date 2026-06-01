"""phase 10 — append-only audit ledger

Revision ID: e5f6d4a7c8b9
Revises: c3d4b2f5a6e7
Create Date: 2026-06-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e5f6d4a7c8b9'
down_revision: Union[str, None] = 'c3d4b2f5a6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'audit_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('seq', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=48), nullable=False),
        sa.Column('entity', sa.String(length=48), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('actor', sa.String(length=255), nullable=True),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('prev_hash', sa.String(length=64), nullable=False),
        sa.Column('hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_events_seq'), 'audit_events', ['seq'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_events_seq'), table_name='audit_events')
    op.drop_table('audit_events')
