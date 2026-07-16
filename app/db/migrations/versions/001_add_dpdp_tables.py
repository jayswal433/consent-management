"""Add DPDP Act 2023 compliant tables

Revision ID: 001_add_dpdp_tables
Revises:
Create Date: 2026-05-21
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "001_add_dpdp_tables"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # dpdp_orgs
    op.create_table(
        "dpdp_orgs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("short_code", sa.String(20), nullable=True),
        sa.Column("color", sa.String(7), nullable=True),
        sa.Column("role", sa.String(50), nullable=True),
        sa.Column("plan", sa.String(30), nullable=False, server_default="free"),
        sa.Column("dpo_name", sa.Text, nullable=True),
        sa.Column("dpo_email", sa.Text, nullable=True),
        sa.Column("dpo_email_hash", sa.String(64), nullable=True),
        sa.Column("dpdp_reg_id", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_dpdp_orgs_name", "dpdp_orgs", ["name"], unique=True)
    op.create_index("idx_dpdp_orgs_short_code", "dpdp_orgs", ["short_code"], unique=True)
    op.create_index("idx_dpdp_orgs_status", "dpdp_orgs", ["status"])
    op.create_index("idx_dpdp_orgs_dpo_email_hash", "dpdp_orgs", ["dpo_email_hash"])
    op.create_index("idx_dpdp_orgs_dpdp_reg_id", "dpdp_orgs", ["dpdp_reg_id"])

    # dpdp_users
    op.create_table(
        "dpdp_users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("dpdp_orgs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("role", sa.String(30), nullable=False, server_default="citizen"),
        sa.Column("name", sa.Text, nullable=True),
        sa.Column("name_hash", sa.String(64), nullable=True),
        sa.Column("email", sa.Text, nullable=True),
        sa.Column("email_hash", sa.String(64), nullable=True),
        sa.Column("phone", sa.Text, nullable=True),
        sa.Column("phone_hash", sa.String(64), nullable=True),
        sa.Column("initials", sa.Text, nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_dpdp_users_email_hash", "dpdp_users", ["email_hash"], unique=True)
    op.create_index("idx_dpdp_users_name_hash", "dpdp_users", ["name_hash"])
    op.create_index("idx_dpdp_users_phone_hash", "dpdp_users", ["phone_hash"])
    op.create_index("idx_dpdp_users_org_id", "dpdp_users", ["org_id"])
    op.create_index("idx_dpdp_users_role", "dpdp_users", ["role"])

    # dpdp_consent_forms
    op.create_table(
        "dpdp_consent_forms",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("dpdp_orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("owner", sa.String(100), nullable=True),
        sa.Column("purpose_short", sa.String(200), nullable=True),
        sa.Column("purpose", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("legal_basis", sa.String(30), nullable=False),
        sa.Column("retention_days", sa.Integer, nullable=False),
        sa.Column("expiry_days", sa.Integer, nullable=False),
        sa.Column("third_parties", sa.JSON, nullable=True),
        sa.Column("user_rights", sa.JSON, nullable=True),
        sa.Column("data_fields", sa.JSON, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("active_version", sa.String(10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_dpdp_consent_forms_code", "dpdp_consent_forms", ["code"], unique=True)
    op.create_index("idx_dpdp_consent_forms_org_id", "dpdp_consent_forms", ["org_id"])
    op.create_index("idx_dpdp_consent_forms_status", "dpdp_consent_forms", ["status"])

    # dpdp_form_versions
    op.create_table(
        "dpdp_form_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("form_id", sa.String(36), sa.ForeignKey("dpdp_consent_forms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("purpose", sa.Text, nullable=False),
        sa.Column("legal_basis", sa.String(30), nullable=False),
        sa.Column("retention_days", sa.Integer, nullable=False),
        sa.Column("expiry_days", sa.Integer, nullable=False),
        sa.Column("third_parties", sa.JSON, nullable=True),
        sa.Column("user_rights", sa.JSON, nullable=True),
        sa.Column("data_fields", sa.JSON, nullable=True),
        sa.Column("custom_body", sa.Text, nullable=True),
        sa.Column("reviewer_note", sa.Text, nullable=True),
        sa.Column("reviewer_sign_off", sa.String(36), nullable=True),
        sa.Column("review_note", sa.Text, nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by", sa.String(36), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("form_id", "version", name="uq_dpdp_form_versions_form_version"),
    )
    op.create_index("idx_dpdp_form_versions_form_id", "dpdp_form_versions", ["form_id"])
    op.create_index("idx_dpdp_form_versions_status", "dpdp_form_versions", ["status"])

    # dpdp_consents
    op.create_table(
        "dpdp_consents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("dpdp_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("form_id", sa.String(36), sa.ForeignKey("dpdp_consent_forms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="granted"),
        sa.Column("optional_fields", sa.Text, nullable=True),
        sa.Column("ip_hash", sa.String(64), nullable=True),
        sa.Column("user_agent_hash", sa.String(64), nullable=True),
        sa.Column("channel", sa.String(20), nullable=False, server_default="web"),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("receipt_token", sa.String(512), nullable=True),
        sa.Column("withdrawal_receipt_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_dpdp_consents_user_id", "dpdp_consents", ["user_id"])
    op.create_index("idx_dpdp_consents_form_id", "dpdp_consents", ["form_id"])
    op.create_index("idx_dpdp_consents_status", "dpdp_consents", ["status"])
    op.create_index("idx_dpdp_consents_expires_at", "dpdp_consents", ["expires_at"])
    op.create_index("idx_dpdp_consents_granted_at", "dpdp_consents", ["granted_at"])
    op.create_index("idx_dpdp_consents_user_form", "dpdp_consents", ["user_id", "form_id"])

    # dpdp_audit_log  (append-only — no updated_at)
    op.create_table(
        "dpdp_audit_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("actor_type", sa.String(20), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("target", sa.String(100), nullable=True),
        sa.Column("version", sa.String(10), nullable=True),
        sa.Column("details", sa.Text, nullable=True),
        sa.Column("prev_hash", sa.String(64), nullable=True),
        sa.Column("hash", sa.String(64), nullable=False),
        sa.Column("org_id", sa.String(36), nullable=True),
    )
    op.create_index("idx_dpdp_audit_log_ts", "dpdp_audit_log", ["ts"])
    op.create_index("idx_dpdp_audit_log_action", "dpdp_audit_log", ["action"])
    op.create_index("idx_dpdp_audit_log_actor", "dpdp_audit_log", ["actor"])
    op.create_index("idx_dpdp_audit_log_org_id", "dpdp_audit_log", ["org_id"])
    op.create_index("idx_dpdp_audit_log_target", "dpdp_audit_log", ["target"])
    op.create_index("idx_dpdp_audit_log_actor_type", "dpdp_audit_log", ["actor_type"])

    # dpdp_nominations
    op.create_table(
        "dpdp_nominations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("dpdp_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nominee_name", sa.Text, nullable=False),
        sa.Column("nominee_email", sa.Text, nullable=False),
        sa.Column("nominee_email_hash", sa.String(64), nullable=True),
        sa.Column("nominee_phone", sa.Text, nullable=True),
        sa.Column("nominee_phone_hash", sa.String(64), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_dpdp_nominations_user_id", "dpdp_nominations", ["user_id"])
    op.create_index("idx_dpdp_nominations_email_hash", "dpdp_nominations", ["nominee_email_hash"])

    # dpdp_async_jobs
    op.create_table(
        "dpdp_async_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("org_id", sa.String(36), nullable=True),
        sa.Column("form_id", sa.String(36), nullable=True),
        sa.Column("initiated_by", sa.String(36), nullable=True),
        sa.Column("total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("processed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("result_url", sa.Text, nullable=True),
        sa.Column("result_url_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_dpdp_async_jobs_job_type", "dpdp_async_jobs", ["job_type"])
    op.create_index("idx_dpdp_async_jobs_status", "dpdp_async_jobs", ["status"])
    op.create_index("idx_dpdp_async_jobs_org_id", "dpdp_async_jobs", ["org_id"])
    op.create_index("idx_dpdp_async_jobs_form_id", "dpdp_async_jobs", ["form_id"])


def downgrade() -> None:
    op.drop_table("dpdp_async_jobs")
    op.drop_table("dpdp_nominations")
    op.drop_table("dpdp_audit_log")
    op.drop_table("dpdp_consents")
    op.drop_table("dpdp_form_versions")
    op.drop_table("dpdp_consent_forms")
    op.drop_table("dpdp_users")
    op.drop_table("dpdp_orgs")
