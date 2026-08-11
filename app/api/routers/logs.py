"""Endpoints for the activity journal."""

from datetime import date as date_type
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUserDep, SessionDep
from app.core.config import settings
from app.crud import activity_crud, log_crud
from app.schemas.log import LogCreate, LogRead
from app.schemas.summary import SummaryResponse

router = APIRouter(prefix="/logs", tags=["logs"])


@router.post(
    "/",
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
