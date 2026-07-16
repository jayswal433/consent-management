"""
Consent record domain model (immutable consent event).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.models.orm.enums import ConsentEventType


@dataclass
class ConsentRecordDomain:
    id: str
    user_id: str
    template_id: str
    domain: str
    visitor_ref: str
    event_type: ConsentEventType
    selected_purposes_json: dict | list
    consent_snapshot: str
    policy_version: str
    s3_key: Optional[str]
    json_hash: Optional[str]
    created_at: datetime

    @classmethod
    def from_orm(cls, row: Any) -> ConsentRecordDomain:
        return cls(
            id=row.id,
            user_id=row.user_id,
            template_id=row.template_id,
            domain=row.domain,
            visitor_ref=row.visitor_ref,
            event_type=row.event_type,
            selected_purposes_json=row.selected_purposes_json,
            consent_snapshot=row.consent_snapshot,
            policy_version=row.policy_version,
            s3_key=row.s3_key,
            json_hash=row.json_hash,
            created_at=row.created_at,
        )

    def to_dict(self, *, include_snapshot: bool = True) -> dict:
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "template_id": self.template_id,
            "domain": self.domain,
            "visitor_ref": self.visitor_ref,
            "event_type": self.event_type.name,
            "selected_purposes_json": self.selected_purposes_json,
            "policy_version": self.policy_version,
            "s3_key": self.s3_key,
            "json_hash": self.json_hash,
            "created_at": self.created_at.isoformat(),
        }
        if include_snapshot:
            data["consent_snapshot"] = self.consent_snapshot
        return data
