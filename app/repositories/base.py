from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Generic, Optional, TypeVar

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def create(self, **kwargs: Any) -> ModelType:
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def get_by_id(self, id_value: Any) -> Optional[ModelType]:
        result = await self.session.execute(
            select(self.model).where(self.model.id == id_value)
        )
        return result.scalar_one_or_none()

    async def get_by_field(
        self, field_name: str, field_value: Any
    ) -> Optional[ModelType]:
        result = await self.session.execute(
            select(self.model).where(
                getattr(self.model, field_name) == field_value
            )
        )
        return result.scalar_one_or_none()

    async def update_by_id(
        self, id_value: Any, **kwargs: Any
    ) -> Optional[ModelType]:
        if hasattr(self.model, "updated_at") and "updated_at" not in kwargs:
            kwargs["updated_at"] = datetime.now(UTC)
        await self.session.execute(
            update(self.model).where(self.model.id == id_value).values(**kwargs)
        )
        await self.session.flush()
        return await self.get_by_id(id_value)

    async def exists_by_field(self, field_name: str, field_value: Any) -> bool:
        result = await self.session.execute(
            select(func.count())
            .select_from(self.model)
            .where(getattr(self.model, field_name) == field_value)
        )
        return bool(result.scalar_one())
