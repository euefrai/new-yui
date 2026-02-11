# ==========================================================
# YUI CAPABILITIES LAYER
# A Yui sabe o que é capaz de fazer; o engine consulta antes de usar.
# Modo lite vs full: desligue capacidades para reduzir custo/latência.
# ==========================================================

from typing import Any, Dict

# Capacidades ativas (True = usar no fluxo; False = pular)
CAPABILITIES: Dict[str, bool] = {
    "memory": True,
    "tools": True,
    "voice": False,
    "planner": True,
    "self_reflection": True,
    "auto_debug": True,
    "vector_memory": True,
    "skills": True,
}

EXECUTION_MODES = ("lite", "full", "autonomous")
DEFAULT_MODE = "full"


def is_enabled(capability: str) -> bool:
    """Retorna True se a capacidade está ativa."""
    return CAPABILITIES.get(capability, False)


def set_capability(capability: str, value: bool) -> None:
    """Liga/desliga uma capacidade em runtime."""
    if capability in CAPABILITIES:
        CAPABILITIES[capability] = value


def get_all() -> Dict[str, Any]:
    """Retorna estado das capacidades (para debug ou UI)."""
    return dict(CAPABILITIES)
