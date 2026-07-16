from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ConsentTrendItem(BaseModel):
    """Consent trend data point."""

    date: str
    granted: int
    withdrawn: int


class ConsentTrendResponse(BaseModel):
    """Consent trend over time response."""

    items: list[ConsentTrendItem]
    days: int


class ConsentSummary(BaseModel):
    """Consent statistics summary."""

    total_granted: int
    total_withdrawn: int
    withdrawal_rate: float
    acceptance_rate: float
    pending_re_consent: int


class FormsByStatus(BaseModel):
    """Form count breakdown by status."""

    active: int
    draft: int
    in_review: int
    archived: int
    deactivated: int


class TopFormItem(BaseModel):
    """Top performing form metrics."""

    form_id: str
    name: str
    granted: int
    withdrawn: int
    acceptance_rate: float

    model_config = ConfigDict(from_attributes=True)


class TopFormsResponse(BaseModel):
    """Top forms response."""

    items: list[TopFormItem]
    limit: int
