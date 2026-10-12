"""Create the initial LifeOps storage schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-12

This first revision delegates the initial schema creation to the SQLAlchemy
metadata shipped with this revision. Follow-up schema changes must use explicit
Alembic operations and must not modify this baseline revision.
"""
from typing import Sequence, Union

from alembic import op

from lifeops.storage.models import Base

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables for a new database."""
    bind = op.get_bind()
    Base.metadata.create_all(\n        bind=bind,\n        tables=[Base.metadata.tables[name] for name in INITIAL_TABLES],\n        checkfirst=True,\n    )


def downgrade() -> None:
    """Drop the initial schema in dependency-safe order."""
    bind = op.get_bind()
    Base.metadata.drop_all(\n        bind=bind,\n        tables=[Base.metadata.tables[name] for name in reversed(INITIAL_TABLES)],\n        checkfirst=True,\n    )
