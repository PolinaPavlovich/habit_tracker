"""The bot's only outbound I/O: an async HTTP client for the habit tracker API.

Nothing else in the package may perform network calls, and nothing anywhere may
reach PostgreSQL directly — the bot is an external client of the REST API.
"""

from decimal import Decimal
from types import TracebackType
from typing import Any, Self

import httpx

from bot.identity import Identity
from bot.schemas import Activity, Log, LogEntry, Summary


class ApiError(Exception):
    """A call to the backend failed.

    ``status_code`` is ``None`` when the request never produced a response at
    all (backend down, DNS failure, timeout), which callers render differently
    from an HTTP error the API deliberately returned.
    """

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class HabitTrackerClient:
    """Thin typed wrapper over the REST API.

    One instance is shared by the whole process so connections are pooled; it is
    created in ``__main__`` and handed to handlers through the dispatcher.
    """

    def __init__(self, *, base_url: str, api_key: str, timeout: float) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            headers={"X-Internal-Api-Key": api_key},
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying connection pool."""
        await self._client.aclose()

    @staticmethod
    def _headers(identity: Identity) -> dict[str, str]:
        """Per-call tenant headers. The shared secret is set on the client."""
        headers = {"X-Telegram-Id": str(identity.telegram_id)}
        if identity.username is not None:
            headers["X-Telegram-Username"] = identity.username
        return headers

    async def _request(
        self,
        method: str,
        url: str,
        *,
        identity: Identity,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Perform one call and return the decoded JSON body.

        Every failure mode is funnelled into :class:`ApiError` so that handlers
        never have to know about httpx.
        """
        try:
            response = await self._client.request(
                method,
                url,
                headers=self._headers(identity),
                json=json,
                params=params,
            )
            # ДОБАВЬ ВОТ ЭТИ ДВЕ СТРОЧКИ:
            if response.status_code != 200:
                print(f"🚨 ОШИБКА API: Статус {response.status_code}, Ответ: {response.text}")
            
            response.raise_for_status() # Это заставит httpx выбросить понятную ошибку
        except httpx.RequestError as error:
            raise ApiError(f"Cannot reach the API: {error}") from error

        if response.is_error:
            raise ApiError(
                _detail_of(response),
                status_code=response.status_code,
            )
        if response.status_code == httpx.codes.NO_CONTENT or not response.content:
            # DELETE answers 204 with an empty body; ``response.json()`` would
            # raise a JSONDecodeError that escapes the ApiError funnel entirely,
            # surfacing to the handler as an unhandled exception.
            return None
        return response.json()

    async def list_activities(self, identity: Identity) -> list[Activity]:
        """Return every activity owned by this user."""
        payload = await self._request("GET", "/activities/", identity=identity)
        return [Activity.model_validate(item) for item in payload]

    async def create_activity(
        self,
        identity: Identity,
        *,
        name: str,
        unit: str,
    ) -> Activity:
        """Create an activity for this user. Raises 409 if the name is taken."""
        payload = await self._request(
            "POST",
            "/activities/",
            identity=identity,
            json={"name": name, "unit": unit},
        )
        return Activity.model_validate(payload)

    async def create_log(
        self,
        identity: Identity,
        *,
        activity_id: int,
        amount: Decimal,
    ) -> Log:
        """Record an amount against one of this user's activities.

        ``amount`` is sent as a string so the decimal survives JSON intact — a
        float round-trip would reintroduce exactly the drift ``Numeric(10, 2)``
        exists to prevent. ``date`` is omitted; the API defaults it to today.
        """
        payload = await self._request(
            "POST",
            "/logs/",
            identity=identity,
            json={"activity_id": activity_id, "amount": str(amount)},
        )
        return Log.model_validate(payload)

    async def list_logs(
        self,
        identity: Identity,
        *,
        limit: int,
        offset: int = 0,
    ) -> list[LogEntry]:
        """Return a page of this user's entries, newest first.

        Ordering is the API's (date descending, id descending as the
        tiebreaker); it is never re-sorted here.
        """
        payload = await self._request(
            "GET",
            "/logs/",
            identity=identity,
            params={"limit": limit, "offset": offset},
        )
        return [LogEntry.model_validate(item) for item in payload]

    async def update_log(
        self,
        identity: Identity,
        *,
        log_id: int,
        amount: Decimal,
    ) -> Log:
        """Change the amount of one of this user's entries.

        ``amount`` is sent as a string for the same reason as in
        :meth:`create_log` — a float round-trip would reintroduce drift.
        """
        payload = await self._request(
            "PATCH",
            f"/logs/{log_id}",
            identity=identity,
            json={"amount": str(amount)},
        )
        return Log.model_validate(payload)

    async def delete_log(self, identity: Identity, *, log_id: int) -> None:
        """Delete one of this user's entries. The activity itself is untouched."""
        await self._request("DELETE", f"/logs/{log_id}", identity=identity)

    async def get_summary(self, identity: Identity, *, days: int) -> Summary:
        """Return this user's aggregated totals for the last ``days`` days."""
        payload = await self._request(
            "GET",
            "/logs/summary",
            identity=identity,
            params={"days": days},
        )
        return Summary.model_validate(payload)


def _detail_of(response: httpx.Response) -> str:
    """Pull FastAPI's ``detail`` out of an error body, falling back to the status."""
    try:
        body = response.json()
    except ValueError:
        return f"API returned HTTP {response.status_code}."
    detail = body.get("detail") if isinstance(body, dict) else None
    if isinstance(detail, str):
        return detail
    return f"API returned HTTP {response.status_code}."
