# ==========================================================
# YUI STATE MACHINE (v2)
# Controla quando executar tools, parar ou responder.
# Sem máquina de estados, agentes grandes viram caos.
# ==========================================================

from enum import Enum
from typing import Any, Callable, Dict, Optional


class AgentState(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    RESPONDING = "responding"


_state = AgentState.IDLE


def get_state() -> AgentState:
    return _state


def set_state(s: AgentState) -> None:
    global _state
    _state = s


def can_execute_tools() -> bool:
    """Só pode executar tools quando em EXECUTING."""
    return _state == AgentState.EXECUTING


def can_respond() -> bool:
    """Pode responder quando em RESPONDING ou IDLE (fallback)."""
    return _state in (AgentState.RESPONDING, AgentState.IDLE)


def transition(to: AgentState) -> None:
    """Transição de estado."""
    set_state(to)


def reset() -> None:
    """Volta ao estado inicial."""
    set_state(AgentState.IDLE)
