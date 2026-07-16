from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class DpdpUserCreateRequest(BaseModel):
    org_id: str | None = None
    role: str = "citizen"
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone: str | None = None
    password: str = Field(min_length=8, max_length=128)


class DpdpUserResponse(BaseModel):
    id: str
    org_id: str | None
    role: str
    name: str | None
    email: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConsentSummaryItem(BaseModel):
    form_id: str
    version: str
    status: str
    granted_at: datetime | None
    expires_at: datetime | None


class DpdpUserDetailResponse(DpdpUserResponse):
    consented_to: list[ConsentSummaryItem] = []


class ErasureRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    request_id: str | None = None


class ErasureResponse(BaseModel):
    deleted: bool
    affected_consents: int
    erasure_receipt_id: str


class PortabilityRequest(BaseModel):
    format: str = "json"


class PortabilityResponse(BaseModel):
    download_url: str
    export_id: str


class NomineeCreateRequest(BaseModel):
    nominee_name: str = Field(min_length=1, max_length=255)
    nominee_email: EmailStr
    nominee_phone: str | None = None


class NomineeResponse(BaseModel):
    nominee_id: str
    created_at: datetime


class RightsResponse(BaseModel):
    rights: list[str]
