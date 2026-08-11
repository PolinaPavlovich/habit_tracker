"""Generic async CRUD operations shared by every entity."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType]):
    """Reusable read/create operations bound to a single ORM model."""

    def __init__(self, model: type[ModelType]) -> None:
        self.model = model

    async def get(self, session: AsyncSession, obj_id: int) -> ModelType | None:
        """Return a single row by primary key, or ``None``."""
        return await session.get(self.model, obj_id)

    async def get_multi(
        self,
        session: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """Return a page of rows ordered by primary key."""
        statement = select(self.model).order_by(self.model.id).offset(skip).limit(limit)
        result = await session.execute(statement)
        return list(result.scalars().all())

    async def create(
        self,
        session: AsyncSession,
        *,
        payload: CreateSchemaType,
        **overrides: Any,
    ) -> ModelType:
        """Persist a new row built from a Pydantic payload."""
        data = payload.model_dump(exclude_unset=False)
        data.update(overrides)
        instance = self.model(**data)
        session.add(instance)
        await session.flush()
        await session.refresh(instance)
        return instance
