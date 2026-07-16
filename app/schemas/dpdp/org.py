from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OrgCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    short_code: str = Field(min_length=1, max_length=20)
    color: str | None = None
    role: str = "data_fiduciary"
    plan: str = "free"
    dpo_name: str = Field(min_length=1, max_length=255)
    dpo_email: EmailStr
    dpdp_reg_id: str | None = None


class OrgUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    dpo_name: str | None = Field(None, min_length=1, max_length=255)
    dpo_email: EmailStr | None = None
    plan: str | None = None
    color: str | None = None
    webhook_url: str | None = None


class OrgResponse(BaseModel):
    id: str
    name: str
    short_code: str
    color: str | None
    role: str
    plan: str
    dpo_name: str | None
    dpo_email: str | None
    dpdp_reg_id: str | None
    webhook_url: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
