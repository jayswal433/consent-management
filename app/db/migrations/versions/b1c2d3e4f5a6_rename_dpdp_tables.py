"""Rename dpdp_ prefixed tables to clean names; drop legacy CMP tables.

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-06-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Disable FK checks so we can drop tables with FK constraints safely
    op.execute("SET FOREIGN_KEY_CHECKS=0")

    # Drop legacy CMP tables (children first, then parent)
    op.drop_table("report_exports")
    op.drop_table("consent_records")
    op.drop_table("api_credentials")
    op.drop_table("consent_purposes")
    op.drop_table("consent_templates")
    op.drop_table("users")

    op.execute("SET FOREIGN_KEY_CHECKS=1")

    # Rename all dpdp_* tables to clean names
    op.rename_table("dpdp_orgs", "orgs")
    op.rename_table("dpdp_users", "users")
    op.rename_table("dpdp_consent_forms", "consent_forms")
    op.rename_table("dpdp_form_versions", "form_versions")
    op.rename_table("dpdp_consents", "consents")
    op.rename_table("dpdp_audit_log", "audit_log")
    op.rename_table("dpdp_nominations", "nominations")
    op.rename_table("dpdp_async_jobs", "async_jobs")
    op.rename_table("dpdp_org_api_keys", "org_api_keys")


def downgrade() -> None:
    # Reverse the dpdp_* table renames
    op.rename_table("org_api_keys", "dpdp_org_api_keys")
    op.rename_table("async_jobs", "dpdp_async_jobs")
    op.rename_table("nominations", "dpdp_nominations")
    op.rename_table("audit_log", "dpdp_audit_log")
    op.rename_table("consents", "dpdp_consents")
    op.rename_table("form_versions", "dpdp_form_versions")
    op.rename_table("consent_forms", "dpdp_consent_forms")
    op.rename_table("users", "dpdp_users")
    op.rename_table("orgs", "dpdp_orgs")
    # NOTE: Legacy CMP tables (users, consent_templates, etc.) were dropped
    # in upgrade() and cannot be automatically recreated in downgrade().
