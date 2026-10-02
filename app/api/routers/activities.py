"""Endpoints for the activity dictionary."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUserDep, SessionDep
from app.crud import activity_crud, log_crud
from app.models.activity import Activity
from app.schemas.activity import ActivityCreate, ActivityDetail, ActivityRead, ActivityUpdate

router = APIRouter(prefix="/activities", tags=["activities"])


@router.post(
    "",
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
    "",
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


async def _owned_activity_or_404(
    session: AsyncSession,
    *,
    user_id: int,
    activity_id: int,
) -> Activity:
    """Fetch the caller's own activity, or raise the one 404 used everywhere.

    An activity owned by somebody else is reported as missing, with the same
    wording as an id that never existed. Never a 403, which would confirm the
    row is out there.
    """
    activity = await activity_crud.get_for_user(
        session,
        user_id=user_id,
        activity_id=activity_id,
    )
    if activity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activity with id {activity_id} does not exist.",
        )
    return activity


@router.get(
    "/{activity_id}",
    response_model=ActivityDetail,
    summary="One activity, with its number of journal entries",
)
async def get_activity(
    activity_id: int,
    session: SessionDep,
    user: CurrentUserDep,
) -> ActivityDetail:
    """Return one of the caller's activities and how many entries it holds."""
    activity = await _owned_activity_or_404(session, user_id=user.id, activity_id=activity_id)
    entries_count = await log_crud.count_for_activity(session, activity_id=activity.id)
    return ActivityDetail(
        **ActivityRead.model_validate(activity).model_dump(),
        entries_count=entries_count,
    )


@router.patch(
    "/{activity_id}",
    response_model=ActivityRead,
    summary="Rename an activity or change its unit",
)
async def update_activity(
    activity_id: int,
    payload: ActivityUpdate,
    session: SessionDep,
    user: CurrentUserDep,
) -> ActivityRead:
    """Edit the caller's own activity. Names stay unique per owner.

    Changing the unit relabels existing entries; their amounts are not
    converted.
    """
    activity = await _owned_activity_or_404(session, user_id=user.id, activity_id=activity_id)
    if payload.name is not None and payload.name != activity.name:
        clash = await activity_crud.get_by_name(session, user_id=user.id, name=payload.name)
        if clash is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"You already have an activity named {payload.name!r}.",
            )
    updated = await activity_crud.update(session, instance=activity, payload=payload)
    return ActivityRead.model_validate(updated)


@router.delete(
    "/{activity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an activity and every entry logged under it",
)
async def delete_activity(
    activity_id: int,
    session: SessionDep,
    user: CurrentUserDep,
) -> None:
    """Remove the activity for good.

    Its journal entries go with it, through ``ON DELETE CASCADE`` on
    ``logs.activity_id``. There is no undo.
    """
    activity = await _owned_activity_or_404(session, user_id=user.id, activity_id=activity_id)
    await activity_crud.remove(session, instance=activity)
