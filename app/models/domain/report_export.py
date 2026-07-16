"""
Async report export domain model.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class ReportExportDomain:
    id: str
    user_id: str
    template_id: str
    domain: str
    from_date: str
    to_date: str
    export_format: str
    status: str
    s3_key: Optional[str]
    created_at: datetime

    @classmethod
    def from_orm(cls, row: Any) -> ReportExportDomain:
        return cls(
            id=row.id,
            user_id=row.user_id,
            template_id=row.template_id,
            domain=row.domain,
            from_date=row.from_date,
            to_date=row.to_date,
            export_format=row.export_format,
            status=row.status,
            s3_key=row.s3_key,
            created_at=row.created_at,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "template_id": self.template_id,
            "domain": self.domain,
            "from_date": self.from_date,
            "to_date": self.to_date,
            "export_format": self.export_format,
            "status": self.status,
            "s3_key": self.s3_key,
            "created_at": self.created_at.isoformat(),
        }
