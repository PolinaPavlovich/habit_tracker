"""Endpoints for the activity dictionary."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import SessionDep
from app.crud import activity_crud
from app.schemas.activity import ActivityCreate, ActivityRead

router = APIRouter(prefix="/activities", tags=["activities"])


@router.post(
    "/",
    response_model=ActivityRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new activity",
)
async def create_activity(payload: ActivityCreate, session: SessionDep) -> ActivityRead:
    """Create an activity. Names are unique across the dictionary."""
    existing = await activity_crud.get_by_name(session, payload.name)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Activity with name {payload.name!r} already exists.",
        )
    activity = await activity_crud.create(session, payload=payload)
    return ActivityRead.model_validate(activity)


@router.get(
    "/",
    response_model=list[ActivityRead],
    summary="List all activities",
)
async def list_activities(
    session: SessionDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[ActivityRead]:
    """Return a page of activities ordered by id."""
    activities = await activity_crud.get_multi(session, skip=skip, limit=limit)
    return [ActivityRead.model_validate(activity) for activity in activities]
