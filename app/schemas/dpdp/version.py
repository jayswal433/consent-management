from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class CreateVersionRequest(BaseModel):
    title: str
    description: str | None = None
    purpose: str
    legal_basis: str
    retention_days: int
    expiry_days: int
    third_parties: list[str] | None = None
    user_rights: list[str] | None = None
    data_fields: list[dict[str, Any]] | None = None
    custom_body: str | None = None
    reviewer_note: str | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v or len(v) > 200:
            raise ValueError("title must be between 1 and 200 characters")
        return v

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, v: str) -> str:
        if not v or len(v) < 30:
            raise ValueError(
                "purpose must be at least 30 characters (DPDP Act §6(1))"
            )
        return v

    @field_validator("retention_days")
    @classmethod
    def validate_retention_days(cls, v: int) -> int:
        if v < 1 or v > 1825:
            raise ValueError("retention_days must be between 1 and 1825 (5 years)")
        return v

    @field_validator("expiry_days")
    @classmethod
    def validate_expiry_days(cls, v: int) -> int:
        if v < 1 or v > 1825:
            raise ValueError("expiry_days must be between 1 and 1825 (5 years)")
        return v

    @field_validator("legal_basis")
    @classmethod
    def validate_legal_basis(cls, v: str) -> str:
        valid_bases = {"consent", "legitimate_interest", "vital_interest"}
        if v not in valid_bases:
            raise ValueError(
                f"legal_basis must be one of {valid_bases}"
            )
        return v

    @field_validator("data_fields")
    @classmethod
    def validate_data_fields(
        cls, v: list[dict[str, Any]] | None
    ) -> list[dict[str, Any]] | None:
        if v is None or len(v) == 0:
            raise ValueError("at least 1 data_field is required")
        return v

    @model_validator(mode="after")
    def validate_expiry_vs_retention(self) -> CreateVersionRequest:
        if self.expiry_days < self.retention_days:
            raise ValueError("expiry_days must be >= retention_days")
        return self


class UpdateVersionRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    purpose: str | None = None
    legal_basis: str | None = None
    retention_days: int | None = None
    expiry_days: int | None = None
    third_parties: list[str] | None = None
    user_rights: list[str] | None = None
    data_fields: list[dict[str, Any]] | None = None
    custom_body: str | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str | None:
        if v is not None and (not v or len(v) > 200):
            raise ValueError("title must be between 1 and 200 characters")
        return v

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, v: str | None) -> str | None:
        if v is not None and (not v or len(v) < 30):
            raise ValueError(
                "purpose must be at least 30 characters (DPDP Act §6(1))"
            )
        return v

    @field_validator("retention_days")
    @classmethod
    def validate_retention_days(cls, v: int | None) -> int | None:
        if v is not None and (v < 1 or v > 1825):
            raise ValueError("retention_days must be between 1 and 1825 (5 years)")
        return v

    @field_validator("expiry_days")
    @classmethod
    def validate_expiry_days(cls, v: int | None) -> int | None:
        if v is not None and (v < 1 or v > 1825):
            raise ValueError("expiry_days must be between 1 and 1825 (5 years)")
        return v

    @field_validator("legal_basis")
    @classmethod
    def validate_legal_basis(cls, v: str | None) -> str | None:
        if v is not None:
            valid_bases = {"consent", "legitimate_interest", "vital_interest"}
            if v not in valid_bases:
                raise ValueError(
                    f"legal_basis must be one of {valid_bases}"
                )
        return v

    @model_validator(mode="after")
    def validate_expiry_vs_retention(self) -> UpdateVersionRequest:
        if (
            self.retention_days is not None
            and self.expiry_days is not None
            and self.expiry_days < self.retention_days
        ):
            raise ValueError("expiry_days must be >= retention_days")
        return self


class SubmitVersionRequest(BaseModel):
    reviewer_note: str | None = None


class PublishVersionRequest(BaseModel):
    reviewer_sign_off: str
    review_note: str | None = None

    @field_validator("reviewer_sign_off")
    @classmethod
    def validate_reviewer_sign_off(cls, v: str) -> str:
        if not v:
            raise ValueError("reviewer_sign_off (admin user_id) is required")
        return v


class RollbackVersionRequest(BaseModel):
    reason: str

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if not v or len(v) < 10:
            raise ValueError("reason must be at least 10 characters")
        return v


class VersionResponse(BaseModel):
    id: str
    form_id: str
    version: str
    status: str
    title: str | None
    purpose: str
    legal_basis: str
    retention_days: int
    expiry_days: int
    data_fields: list[dict[str, Any]] | None
    published_at: datetime | None
    published_by: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VersionDiffResponse(BaseModel):
    added: list[dict[str, Any]]
    removed: list[dict[str, Any]]
    changed: list[dict[str, Any]]
