"""Rendering and parsing of the values that cross the chat boundary.

Everything the user typed — activity names, units — is HTML-escaped before it
goes back out, because messages are sent with ``parse_mode=HTML``.
"""

from decimal import Decimal, InvalidOperation
from html import escape

from bot.client import ApiError
from bot.schemas import ActivitySummary, Summary

# The envelope of ``Log.amount``: Numeric(10, 2).
MAX_AMOUNT = Decimal("99999999.99")
MAX_DECIMAL_PLACES = 2


def parse_amount(raw: str) -> Decimal:
    """Parse a typed amount, mirroring the API's own validation.

    The same envelope ``LogCreate`` enforces is checked here so the user gets a
    sentence instead of a 422. A comma is accepted as the decimal separator.

    Raises:
        ValueError: with a message meant to be shown to the user.
    """
    candidate = raw.strip().replace(",", ".")
    try:
        amount = Decimal(candidate)
    except InvalidOperation:
        raise ValueError("That doesn't look like a number. Try something like 7.5") from None

    if not amount.is_finite():
        raise ValueError("That doesn't look like a number. Try something like 7.5")
    if amount <= 0:
        raise ValueError("The amount has to be greater than zero.")
    if -amount.as_tuple().exponent > MAX_DECIMAL_PLACES:  # type: ignore[operator]
        raise ValueError("Use at most two decimal places.")
    if amount > MAX_AMOUNT:
        raise ValueError(f"That's too large — the maximum is {MAX_AMOUNT}.")
    return amount


def format_amount(amount: Decimal) -> str:
    """Render an amount without trailing zeros: 7.50 → "7.5", 21.00 → "21"."""
    return f"{amount.normalize():f}"


def format_log_confirmation(activity_name: str, unit: str, amount: Decimal) -> str:
    """Confirmation shown after a journal entry is accepted."""
    return (
        f"✅ Logged <b>{format_amount(amount)} {escape(unit)}</b> "
        f"of {escape(activity_name)}."
    )


def format_summary(summary: Summary) -> str:
    """Render the aggregated totals as a monospace table.

    Rows arrive already ordered by the API (total descending, activity id as the
    tiebreaker); they are never re-sorted here.
    """
    header = (
        f"📊 <b>{summary.period_start} → {summary.period_end}</b> "
        f"({summary.days} days)"
    )
    if not summary.items:
        return f"{header}\n\nNothing logged in this window yet."

    width = max(len(item.activity_name) for item in summary.items)
    rows = "\n".join(_summary_row(item, width) for item in summary.items)
    return f"{header}\n\n<pre>{escape(rows)}</pre>"


def _summary_row(item: ActivitySummary, width: int) -> str:
    """One padded line of the summary table, before escaping."""
    total = f"{format_amount(item.total_amount)} {item.unit}"
    return f"{item.activity_name:<{width}}  {total:>12}  ({item.entries_count})"


def describe_api_error(error: ApiError) -> str:
    """Turn a backend failure into something worth reading in a chat."""
    if error.status_code is None:
        return "⚠️ The tracker backend is unreachable right now. Try again in a moment."
    if error.status_code == 404:
        return "⚠️ That activity no longer exists. Send /log to start over."
    if error.status_code == 409:
        return f"⚠️ {error.message}"
    if error.status_code in (401, 403):
        return "⚠️ The bot is not authorised to talk to the backend. Check INTERNAL_API_KEY."
    return f"⚠️ {error.message}"
