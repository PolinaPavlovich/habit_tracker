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

    async def update(
        self,
        session: AsyncSession,
        *,
        instance: ModelType,
        payload: BaseModel,
    ) -> ModelType:
        """Apply a partial payload to a row the caller has already fetched.

        Takes the *instance*, never an id — see :meth:`remove` for why.
        ``exclude_unset`` keeps an omitted field omitted rather than writing
        the schema's default over a stored value.
        """
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(instance, field, value)
        await session.flush()
        await session.refresh(instance)
        return instance

    async def remove(self, session: AsyncSession, *, instance: ModelType) -> None:
        """Delete a row the caller has already fetched.

        Deliberately takes the *instance* rather than an id. Deleting by id
        would need a lookup here, and the only lookup available on this class is
        the tenant-blind :meth:`get` — which would let a caller destroy another
        user's row by passing its id. Requiring an instance means ownership has
        necessarily been proven by whatever scoped query produced it.
        """
        await session.delete(instance)
        await session.flush()
