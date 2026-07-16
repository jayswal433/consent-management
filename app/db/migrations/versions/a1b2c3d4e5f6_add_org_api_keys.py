"""Add organization API keys table and webhook_url to orgs

Revision ID: a1b2c3d4e5f6
Revises: 3877ed4eac83
Create Date: 2026-06-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "3877ed4eac83"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add dpdp_org_api_keys table and webhook_url column to dpdp_orgs."""
    op.add_column(
        "dpdp_orgs",
        sa.Column("webhook_url", sa.String(length=500), nullable=True),
    )

    op.create_table(
        "dpdp_org_api_keys",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("key_prefix", sa.String(length=16), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.String(length=1), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["dpdp_orgs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "idx_dpdp_org_api_keys_org_id",
        "dpdp_org_api_keys",
        ["org_id"],
        unique=False,
    )
    op.create_index(
        "idx_dpdp_org_api_keys_is_active",
        "dpdp_org_api_keys",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        "ix_dpdp_org_api_keys_key_prefix",
        "dpdp_org_api_keys",
        ["key_prefix"],
        unique=True,
    )
    op.create_index(
        "ix_dpdp_org_api_keys_key_hash",
        "dpdp_org_api_keys",
        ["key_hash"],
        unique=True,
    )
    op.create_index(
        "ix_dpdp_org_api_keys_id",
        "dpdp_org_api_keys",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop dpdp_org_api_keys table and webhook_url column from dpdp_orgs."""
    op.drop_table("dpdp_org_api_keys")
    op.drop_column("dpdp_orgs", "webhook_url")
