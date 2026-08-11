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
