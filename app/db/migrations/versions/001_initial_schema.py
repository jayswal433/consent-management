"""Initial CMP schema.

Revision ID: 001_initial
Revises:
Create Date: 2026-05-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    op.create_table(
        "api_credentials",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("api_key_hash", sa.String(length=255), nullable=False),
        sa.Column("status", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_api_credentials_id"), "api_credentials", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_api_credentials_user_id"),
        "api_credentials",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "consent_templates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("template_name", sa.String(length=255), nullable=False),
        sa.Column("logo_url", sa.String(length=1024), nullable=True),
        sa.Column("header_text", sa.String(length=500), nullable=False),
        sa.Column("body_text", sa.String(length=4000), nullable=False),
        sa.Column("footer_text", sa.String(length=2000), nullable=True),
        sa.Column("buttons_json", sa.JSON(), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("status", sa.Integer(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "version", name="uq_consent_templates_user_version"
        ),
    )
    op.create_index(
        op.f("ix_consent_templates_id"), "consent_templates", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_consent_templates_user_id"),
        "consent_templates",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "consent_purposes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("template_id", sa.String(length=36), nullable=False),
        sa.Column("purpose_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("data_fields_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["template_id"], ["consent_templates.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_consent_purposes_id"), "consent_purposes", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_consent_purposes_template_id"),
        "consent_purposes",
        ["template_id"],
        unique=False,
    )

    op.create_table(
        "consent_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("template_id", sa.String(length=36), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("visitor_ref", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.Integer(), nullable=False),
        sa.Column("selected_purposes_json", sa.JSON(), nullable=False),
        sa.Column("consent_snapshot", sa.Text(), nullable=False),
        sa.Column("policy_version", sa.String(length=50), nullable=False),
        sa.Column("s3_key", sa.String(length=1024), nullable=True),
        sa.Column("json_hash", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["template_id"], ["consent_templates.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_consent_records_domain_visitor_created_at",
        "consent_records",
        ["domain", "visitor_ref", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_consent_records_domain_visitor_ref",
        "consent_records",
        ["domain", "visitor_ref"],
        unique=False,
    )
    op.create_index(
        op.f("ix_consent_records_id"), "consent_records", ["id"], unique=False
    )
    op.create_index(
        "idx_consent_records_template_created_at",
        "consent_records",
        ["template_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_consent_records_template_id"),
        "consent_records",
        ["template_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_consent_records_user_id"),
        "consent_records",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "report_exports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("template_id", sa.String(length=36), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("from_date", sa.String(length=10), nullable=False),
        sa.Column("to_date", sa.String(length=10), nullable=False),
        sa.Column("export_format", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("s3_key", sa.String(length=1024), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_report_exports_domain"), "report_exports", ["domain"], unique=False
    )
    op.create_index(
        op.f("ix_report_exports_id"), "report_exports", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_report_exports_template_id"),
        "report_exports",
        ["template_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_report_exports_user_id"),
        "report_exports",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("report_exports")
    op.drop_table("consent_records")
    op.drop_table("consent_purposes")
    op.drop_table("consent_templates")
    op.drop_table("api_credentials")
    op.drop_table("users")
