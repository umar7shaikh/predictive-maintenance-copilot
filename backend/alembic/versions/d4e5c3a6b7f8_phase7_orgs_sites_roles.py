"""phase 7 — organizations, sites, roles

Adds organizations + sites, users.org_id/role, machines.site_id. A default
organization is backfilled for any existing users so single-deployment installs
keep working.

Revision ID: d4e5c3a6b7f8
Revises: b2c3a1e4f5d6
Create Date: 2026-06-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5c3a6b7f8'
down_revision: Union[str, None] = 'b2c3a1e4f5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'organizations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('country', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'sites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('location', sa.String(length=128), nullable=True),
        sa.Column('region', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sites_org_id'), 'sites', ['org_id'], unique=False)

    op.add_column('users', sa.Column('org_id', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('role', sa.String(length=16), nullable=False,
                                     server_default='operator'))
    op.create_foreign_key('fk_users_org', 'users', 'organizations', ['org_id'], ['id'])

    op.add_column('machines', sa.Column('site_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_machines_site', 'machines', 'sites', ['site_id'], ['id'])

    # --- backfill: one default org, attach all existing users, first user = owner ---
    conn = op.get_bind()
    has_users = conn.execute(sa.text("SELECT COUNT(*) FROM users")).scalar()
    if has_users:
        conn.execute(sa.text(
            "INSERT INTO organizations (name, country, created_at) "
            "VALUES ('Default Organization', 'IN', now())"
        ))
        org_id = conn.execute(sa.text("SELECT id FROM organizations ORDER BY id ASC LIMIT 1")).scalar()
        conn.execute(sa.text("UPDATE users SET org_id = :oid"), {"oid": org_id})
        first_id = conn.execute(sa.text("SELECT id FROM users ORDER BY id ASC LIMIT 1")).scalar()
        conn.execute(sa.text("UPDATE users SET role = 'owner' WHERE id = :uid"), {"uid": first_id})


def downgrade() -> None:
    op.drop_constraint('fk_machines_site', 'machines', type_='foreignkey')
    op.drop_column('machines', 'site_id')
    op.drop_constraint('fk_users_org', 'users', type_='foreignkey')
    op.drop_column('users', 'role')
    op.drop_column('users', 'org_id')
    op.drop_index(op.f('ix_sites_org_id'), table_name='sites')
    op.drop_table('sites')
    op.drop_table('organizations')
