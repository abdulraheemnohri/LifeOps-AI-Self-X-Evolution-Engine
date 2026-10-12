"""Add workflow tables

Revision ID: 0002_add_workflow_tables
Revises: 0001_initial
Create Date: 2024-10-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '0002_add_workflow_tables'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade():
    # Create workflow_definitions table
    op.create_table(
        'workflow_definitions',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('status', sa.String(length=32), nullable=False, default='draft'),
        sa.Column('definition', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    
    # Create workflow_runs table
    op.create_table(
        'workflow_runs',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('workflow_id', sa.String(length=64), sa.ForeignKey('workflow_definitions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('version', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, default='running'),
        sa.Column('step_results', sa.JSON(), nullable=False, default={}),
        sa.Column('logs', sa.Text(), nullable=False, default=''),
        sa.Column('started_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('workflow_runs')
    op.drop_table('workflow_definitions')
