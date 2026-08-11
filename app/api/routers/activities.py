"""Endpoints for the activity dictionary."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUserDep, SessionDep
from app.crud import activity_crud
from app.schemas.activity import ActivityCreate, ActivityRead

router = APIRouter(prefix="/activities", tags=["activities"])


@router.post(
    "/",
    response_model=ActivityRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new activity",
)
async def create_activity(
    payload: ActivityCreate,
    session: SessionDep,
    user: CurrentUserDep,
) -> ActivityRead:
    """Create an activity owned by the caller. Names are unique per owner."""
    existing = await activity_crud.get_by_name(
        session,
        user_id=user.id,
        name=payload.name,
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"You already have an activity named {payload.name!r}.",
        )
    activity = await activity_crud.create(session, payload=payload, user_id=user.id)
    return ActivityRead.model_validate(activity)


@router.get(
    "/",
    response_model=list[ActivityRead],
    summary="List the caller's activities",
)
async def list_activities(
    session: SessionDep,
    user: CurrentUserDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[ActivityRead]:
    """Return a page of the caller's activities, ordered by id."""
    activities = await activity_crud.get_multi_for_user(
        session,
        user_id=user.id,
        skip=skip,
        limit=limit,
    )
    return [ActivityRead.model_validate(activity) for activity in activities]
