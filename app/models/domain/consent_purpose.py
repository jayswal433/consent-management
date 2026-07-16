"""
Consent purpose domain model.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class ConsentPurposeDomain:
    id: str
    template_id: str
    name: str
    description: Optional[str]
    data_fields_json: dict | list
    created_at: datetime

    @classmethod
    def from_orm(cls, row: Any) -> ConsentPurposeDomain:
        return cls(
            id=row.id,
            template_id=row.template_id,
            name=row.name,
            description=row.description,
            data_fields_json=row.data_fields_json,
            created_at=row.created_at,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "data_fields_json": self.data_fields_json,
            "created_at": self.created_at.isoformat(),
        }
