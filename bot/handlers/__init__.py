"""Handler routers, in the order the dispatcher should consult them.

``common`` comes first so that /start, /help and /cancel are matched before the
state-bound message handlers in the other modules, which would otherwise
swallow those commands as free text.

``fallback`` comes last: it answers any button press nothing else claimed.
"""

from aiogram import Router

from bot.handlers import activities, common, fallback, habits, history, log, summary

ROUTERS: tuple[Router, ...] = (
    common.router,
    activities.router,
    habits.router,
    log.router,
    history.router,
    summary.router,
    fallback.router,
)

__all__ = ["ROUTERS"]
