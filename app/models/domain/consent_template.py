"""
Consent template domain model.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from app.models.orm.enums import TemplateStatus


@dataclass
class ConsentTemplateDomain:
    id: str
    user_id: str
    template_name: str
    logo_url: Optional[str]
    header_text: str
    body_text: str
    footer_text: Optional[str]
    buttons_json: dict | list
    version: str
    status: TemplateStatus
    published_at: Optional[datetime]
    created_at: datetime

    @classmethod
    def from_orm(cls, row: Any) -> ConsentTemplateDomain:
        return cls(
            id=row.id,
            user_id=row.user_id,
            template_name=row.template_name,
            logo_url=row.logo_url,
            header_text=row.header_text,
            body_text=row.body_text,
            footer_text=row.footer_text,
            buttons_json=row.buttons_json,
            version=row.version,
            status=row.status,
            published_at=row.published_at,
            created_at=row.created_at,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "template_name": self.template_name,
            "logo_url": self.logo_url,
            "header_text": self.header_text,
            "body_text": self.body_text,
            "footer_text": self.footer_text,
            "buttons_json": self.buttons_json,
            "version": self.version,
            "status": (
                self.status.name
                if isinstance(self.status, TemplateStatus)
                else str(self.status)
            ),
            "published_at": (
                self.published_at.isoformat() if self.published_at else None
            ),
            "created_at": self.created_at.isoformat(),
        }
