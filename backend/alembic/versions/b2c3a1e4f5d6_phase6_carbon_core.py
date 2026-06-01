"""phase 6 — energy & carbon core

Adds emission factors, energy sources, utility bills, fuel logs, emission records,
and avoided-impact tables; plus machines.rated_power_kw and sensor_readings.power_kw.

Revision ID: b2c3a1e4f5d6
Revises: d7d1f1965f5a
Create Date: 2026-06-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3a1e4f5d6'
down_revision: Union[str, None] = 'd7d1f1965f5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- new columns on existing tables ---
    op.add_column('machines', sa.Column('rated_power_kw', sa.Float(), nullable=True))
    op.add_column('sensor_readings', sa.Column('power_kw', sa.Float(), nullable=True))

    # --- emission factors (reference data) ---
    op.create_table(
        'emission_factors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('region', sa.String(length=32), nullable=False),
        sa.Column('activity_type', sa.String(length=32), nullable=False),
        sa.Column('scope', sa.Integer(), nullable=False),
        sa.Column('kgco2e_per_unit', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(length=16), nullable=False),
        sa.Column('source', sa.String(length=255), nullable=False),
        sa.Column('version', sa.String(length=32), nullable=True),
        sa.Column('valid_from', sa.DateTime(), nullable=True),
        sa.Column('valid_to', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_emission_factors_region'), 'emission_factors', ['region'], unique=False)

    # --- energy sources ---
    op.create_table(
        'energy_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('source_type', sa.String(length=32), nullable=False),
        sa.Column('region', sa.String(length=32), nullable=False),
        sa.Column('genset_litres_per_hour', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- utility bills (Scope 2 input) ---
    op.create_table(
        'utility_bills',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=True),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('kwh', sa.Float(), nullable=False),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=8), nullable=False),
        sa.Column('region', sa.String(length=32), nullable=False),
        sa.Column('data_quality', sa.String(length=16), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['source_id'], ['energy_sources.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- fuel logs (Scope 1 input) ---
    op.create_table(
        'fuel_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=True),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('fuel_type', sa.String(length=32), nullable=False),
        sa.Column('litres', sa.Float(), nullable=True),
        sa.Column('runtime_hours', sa.Float(), nullable=True),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=8), nullable=False),
        sa.Column('region', sa.String(length=32), nullable=False),
        sa.Column('data_quality', sa.String(length=16), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['source_id'], ['energy_sources.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- computed emission records ---
    op.create_table(
        'emission_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('scope', sa.Integer(), nullable=False),
        sa.Column('source_type', sa.String(length=32), nullable=False),
        sa.Column('activity_type', sa.String(length=32), nullable=False),
        sa.Column('activity_amount', sa.Float(), nullable=False),
        sa.Column('activity_unit', sa.String(length=16), nullable=False),
        sa.Column('factor_id', sa.Integer(), nullable=True),
        sa.Column('kgco2e', sa.Float(), nullable=False),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=8), nullable=True),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('data_quality', sa.String(length=16), nullable=False),
        sa.Column('origin', sa.String(length=32), nullable=True),
        sa.Column('origin_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['factor_id'], ['emission_factors.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_emission_records_scope'), 'emission_records', ['scope'], unique=False)

    # --- avoided impacts ---
    op.create_table(
        'avoided_impacts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('machine_id', sa.Integer(), nullable=True),
        sa.Column('maintenance_log_id', sa.Integer(), nullable=True),
        sa.Column('wasted_kwh', sa.Float(), nullable=False),
        sa.Column('avoided_kgco2e', sa.Float(), nullable=False),
        sa.Column('saveable_cost', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=8), nullable=True),
        sa.Column('severity', sa.String(length=16), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['machine_id'], ['machines.id'], ),
        sa.ForeignKeyConstraint(['maintenance_log_id'], ['maintenance_logs.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('avoided_impacts')
    op.drop_index(op.f('ix_emission_records_scope'), table_name='emission_records')
    op.drop_table('emission_records')
    op.drop_table('fuel_logs')
    op.drop_table('utility_bills')
    op.drop_table('energy_sources')
    op.drop_index(op.f('ix_emission_factors_region'), table_name='emission_factors')
    op.drop_table('emission_factors')
    op.drop_column('sensor_readings', 'power_kw')
    op.drop_column('machines', 'rated_power_kw')
