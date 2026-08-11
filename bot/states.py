"""FSM state groups for the multi-step flows.

Backed by ``MemoryStorage``: a bot restart drops half-finished entries, which is
acceptable — nothing is written to the API until a flow completes.
"""

from aiogram.fsm.state import State, StatesGroup


class LogStates(StatesGroup):
    """The ``/log`` flow, when the user opts to type a custom amount."""

    waiting_amount = State()


class ActivityStates(StatesGroup):
    """The ``/new`` flow: ask for a name, then a unit."""

    waiting_name = State()
    waiting_unit = State()


class HistoryStates(StatesGroup):
    """The ``/history`` flow, while waiting for a replacement amount.

    Separate from :class:`LogStates` on purpose: both wait for a typed number,
    and a shared state would let the ``/log`` handler answer a message meant for
    an edit — writing a new entry instead of amending the one in hand.
    """

    waiting_new_amount = State()
