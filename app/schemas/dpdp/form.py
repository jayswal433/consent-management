from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class CreateFormRequest(BaseModel):
    name: str
    code: str
    org_id: str
    owner: str
    purpose_short: str
    purpose: str
    description: str | None = None
    legal_basis: str
    retention_days: int
    expiry_days: int
    third_parties: list[str] | None = None
    user_rights: list[str] | None = None
    data_fields: list[dict[str, Any]] | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or len(v) > 80:
            raise ValueError("name must be between 1 and 80 characters")
        return v

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v or len(v) > 30:
            raise ValueError("code must be between 1 and 30 characters")
        if not v.isupper() or not all(c.isalnum() or c == "_" for c in v):
            raise ValueError("code must be UPPERCASE alphanumeric with optional underscores")
        return v

    @field_validator("purpose_short")
    @classmethod
    def validate_purpose_short(cls, v: str) -> str:
        if not v or len(v) > 200:
            raise ValueError("purpose_short must be between 1 and 200 characters")
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

    @model_validator(mode="after")
    def validate_expiry_vs_retention(self) -> CreateFormRequest:
        if self.expiry_days < self.retention_days:
            raise ValueError("expiry_days must be >= retention_days")
        return self


class UpdateFormRequest(BaseModel):
    owner: str | None = None
    purpose_short: str | None = None

    @field_validator("owner")
    @classmethod
    def validate_owner(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 100:
            raise ValueError("owner must be max 100 characters")
        return v

    @field_validator("purpose_short")
    @classmethod
    def validate_purpose_short(cls, v: str | None) -> str | None:
        if v is not None and (not v or len(v) > 200):
            raise ValueError("purpose_short must be between 1 and 200 characters")
        return v


class DeactivateFormRequest(BaseModel):
    reason: str
    notify_dpo: bool = False

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if not v or len(v) < 10:
            raise ValueError("reason must be at least 10 characters")
        return v


class FormListItem(BaseModel):
    id: str
    name: str
    code: str
    status: str
    active_version: str | None
    org_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FormDetailResponse(BaseModel):
    id: str
    name: str
    code: str
    org_id: str
    owner: str | None
    status: str
    active_version: str | None
    purpose: str
    purpose_short: str | None
    description: str | None
    legal_basis: str
    retention_days: int
    expiry_days: int
    third_parties: list[str] | None
    user_rights: list[str] | None
    data_fields: list[dict[str, Any]] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FormCreateResponse(BaseModel):
    id: str
    code: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PublishedFormItem(BaseModel):
    id: str
    name: str
    code: str
    status: str
    org_id: str
    active_version: str | None
    published_at: datetime | None
    published_by: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LatestPublishedFormResponse(BaseModel):
    # Form-level fields
    id: str
    name: str
    code: str
    org_id: str
    owner: str | None
    status: str
    active_version: str | None
    purpose_short: str | None
    created_at: datetime
    updated_at: datetime
    # Version-level fields
    version_id: str | None
    version: str | None
    title: str | None
    description: str | None
    purpose: str | None
    legal_basis: str | None
    retention_days: int | None
    expiry_days: int | None
    third_parties: list[str] | None
    user_rights: list[str] | None
    data_fields: list[dict[str, Any]] | None
    custom_body: str | None
    published_at: datetime | None
    published_by: str | None

    model_config = ConfigDict(from_attributes=True)
