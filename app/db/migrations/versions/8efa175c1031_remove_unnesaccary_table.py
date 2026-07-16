"""remove unnesaccary table

Revision ID: 8efa175c1031
Revises: 88a79298c0fb
Create Date: 2026-05-22 12:35:09.611678

Note:
    This migration was originally an exact duplicate of ``88a79298c0fb``.
    Because ``88a79298c0fb`` runs first in the chain, re-running the same
    operations here failed (e.g. dropping an already-dropped index), which
    broke the migration chain and prevented later revisions from applying.
    The bodies are intentionally no-ops to preserve the revision graph while
    skipping the duplicated work.
"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '8efa175c1031'
down_revision: Union[str, None] = '88a79298c0fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No-op: operations were a duplicate of revision 88a79298c0fb.
    pass


def downgrade() -> None:
    # No-op: nothing was applied in upgrade().
    pass
