"""Pydantic schemas for organization API key management."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CreateApiKeyRequest(BaseModel):
    """Request to create a new API key."""

    label: str = Field(min_length=1, max_length=100)
    expires_at: Optional[datetime] = Field(None)


class ApiKeyCreateResponse(BaseModel):
    """Response when creating an API key (includes raw key shown once)."""

    id: str
    label: str
    key_prefix: str
    raw_key: str = Field(description="Full API key - shown only once, never logged")
    org_id: str
    created_at: datetime
    expires_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ApiKeyListItem(BaseModel):
    """Single API key item in list response (no raw key)."""

    id: str
    label: str
    key_prefix: str
    is_active: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
