"""
API credential domain model.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.models.orm.enums import CredentialStatus


@dataclass
class ApiCredentialDomain:
    id: str
    user_id: str
    api_key_hash: str
    status: CredentialStatus
    created_at: datetime

    @classmethod
    def from_orm(cls, row: Any) -> ApiCredentialDomain:
        return cls(
            id=row.id,
            user_id=row.user_id,
            api_key_hash=row.api_key_hash,
            status=row.status,
            created_at=row.created_at,
        )

    @property
    def is_active(self) -> bool:
        return self.status == CredentialStatus.active

    def to_dict(self, *, include_secret_hash: bool = False) -> dict:
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "status": (
                self.status.name
                if isinstance(self.status, CredentialStatus)
                else str(self.status)
            ),
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active,
        }
        if include_secret_hash:
            data["api_key_hash"] = self.api_key_hash
        return data
