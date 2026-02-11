# ==========================================================
# YUI CAPABILITIES LAYER
# A Yui sabe o que é capaz de fazer; o engine consulta antes de usar.
# Modo LITE = menos RAM, menor custo. Modo FULL = todas as capacidades.
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
    "goals": True,
}

EXECUTION_MODES = ("lite", "full", "autonomous")
DEFAULT_MODE = "full"

# Presets para deploy (ex: Render com pouca RAM)
MODE_LITE = {
    "planner": False,
    "self_reflection": False,
    "auto_debug": False,
    "vector_memory": False,
    "goals": False,
}

MODE_FULL = {
    "planner": True,
    "self_reflection": True,
    "auto_debug": True,
    "vector_memory": True,
    "goals": True,
}


def is_enabled(capability: str) -> bool:
    """Retorna True se a capacidade está ativa."""
    return CAPABILITIES.get(capability, False)


def set_capability(capability: str, value: bool) -> None:
    """Liga/desliga uma capacidade em runtime."""
    if capability in CAPABILITIES:
        CAPABILITIES[capability] = value


def apply_mode(mode: str) -> None:
    """Aplica preset LITE ou FULL. Útil para deploy (ex: Render, Zeabur -> LITE)."""
    preset = MODE_LITE if mode == "lite" else MODE_FULL
    for cap, val in preset.items():
        if cap in CAPABILITIES:
            CAPABILITIES[cap] = val


def get_all() -> Dict[str, Any]:
    """Retorna estado das capacidades (para debug ou UI)."""
    return dict(CAPABILITIES)
