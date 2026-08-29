"""Endpoints for the activity journal."""

from datetime import date as date_type
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUserDep, SessionDep
from app.core.config import settings
from app.crud import activity_crud, log_crud
from app.schemas.log import LogCreate, LogListItem, LogRead, LogUpdate
from app.schemas.summary import SummaryResponse

router = APIRouter(prefix="/logs", tags=["logs"])


@router.post(
    "",
    response_model=LogRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add an entry to the journal",
)
async def create_log(
    payload: LogCreate,
    session: SessionDep,
    user: CurrentUserDep,
) -> LogRead:
    """Record an amount for one of the caller's activities.

    An activity owned by somebody else is reported as missing, exactly like an
    id that does not exist, so the response never confirms it is out there.
    """
    activity = await activity_crud.get_for_user(
        session,
        user_id=user.id,
        activity_id=payload.activity_id,
    )
    if activity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activity with id {payload.activity_id} does not exist.",
        )
    entry_date = payload.date if payload.date is not None else date_type.today()
    log = await log_crud.create(session, payload=payload, date=entry_date)
    return LogRead.model_validate(log)


@router.get(
    "",
    response_model=list[LogListItem],
    summary="Recent journal entries, newest first",
)
async def list_logs(
    session: SessionDep,
    user: CurrentUserDep,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[LogListItem]:
    """Return a page of the caller's own entries, joined with their activities."""
    return await log_crud.get_recent_for_user(
        session,
        user_id=user.id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/summary",
    response_model=SummaryResponse,
    summary="Aggregated statistics for the last 7 days",
)
async def get_summary(
    session: SessionDep,
    user: CurrentUserDep,
    days: Annotated[int, Query(ge=1, le=365)] = settings.summary_window_days,
) -> SummaryResponse:
    """Sum the caller's logged amounts per activity over a window including today."""
    period_start, period_end = log_crud.period_bounds(days)
    items = await log_crud.get_summary(
        session,
        user_id=user.id,
        period_start=period_start,
        period_end=period_end,
    )
    return SummaryResponse(
        period_start=period_start,
        period_end=period_end,
        days=days,
        items=items,
    )


# Everything below matches "/logs/{log_id}". It must stay declared *after*
# "/logs/summary", or FastAPI would resolve "summary" as a log id.


@router.patch(
    "/{log_id}",
    response_model=LogRead,
    summary="Change the amount of one journal entry",
)
async def update_log(
    log_id: int,
    payload: LogUpdate,
    session: SessionDep,
    user: CurrentUserDep,
) -> LogRead:
    """Edit the caller's own entry.

    An entry owned by somebody else is reported as missing — the same 404 as an
    id that never existed, never a 403, which would confirm it is out there.
    """
    log = await log_crud.get_for_user(session, user_id=user.id, log_id=log_id)
    if log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Log with id {log_id} does not exist.",
        )
    updated = await log_crud.update(session, instance=log, payload=payload)
    return LogRead.model_validate(updated)


@router.delete(
    "/{log_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete one journal entry",
)
async def delete_log(
    log_id: int,
    session: SessionDep,
    user: CurrentUserDep,
) -> None:
    """Remove a single entry, leaving its activity alone.

    Only the journal row goes; the activity it points at is untouched, so this
    never cascades into the dictionary of activities.
    """
    log = await log_crud.get_for_user(session, user_id=user.id, log_id=log_id)
    if log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Log with id {log_id} does not exist.",
        )
    await log_crud.remove(session, instance=log)
