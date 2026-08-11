"""Handler routers, in the order the dispatcher should consult them.

``common`` comes first so that /start, /help and /cancel are matched before the
state-bound message handlers in the other modules, which would otherwise
swallow those commands as free text.
"""

from aiogram import Router

from bot.handlers import activities, common, log, summary

ROUTERS: tuple[Router, ...] = (
    common.router,
    activities.router,
    log.router,
    summary.router,
)

__all__ = ["ROUTERS"]
