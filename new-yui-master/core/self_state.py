# ==========================================================
# YUI SELF STATE
# A IA raciocina sobre o próprio estado: última ação, erro, confiança, modo.
# Base para auto-ajuste, auto-correção e personalidade dinâmica.
# ==========================================================

from typing import Any, Dict

_state: Dict[str, Any] = {
    "last_action": "",
    "last_error": "",
    "confidence_level": 1.0,
    "execution_mode": "full",
}


def get(key: str) -> Any:
    return _state.get(key)


def set_state(key: str, value: Any) -> None:
    if key in _state:
        _state[key] = value


def set_last_action(action: str) -> None:
    _state["last_action"] = action or ""


def set_last_error(err: str) -> None:
    _state["last_error"] = err or ""


def set_confidence(level: float) -> None:
    _state["confidence_level"] = max(0.0, min(1.0, level))


def set_execution_mode(mode: str) -> None:
    if mode in ("lite", "full", "autonomous"):
        _state["execution_mode"] = mode


def clear_error() -> None:
    """Limpa o último erro (ex: após sucesso)."""
    _state["last_error"] = ""


def reset() -> None:
    """Reseta o estado para valores iniciais (nova sessão)."""
    _state.update({
        "last_action": "",
        "last_error": "",
        "confidence_level": 1.0,
        "execution_mode": "full",
    })


def get_all() -> Dict[str, Any]:
    return dict(_state)


def to_prompt_snippet() -> str:
    """Texto curto para injetar no prompt (estado interno da Yui)."""
    a = _state.get("last_action") or "nenhuma"
    e = _state.get("last_error")
    c = _state.get("confidence_level", 1.0)
    m = _state.get("execution_mode") or "full"
    lines = [f"Estado interno: última ação={a}, confiança={c:.2f}, modo={m}."]
    if e:
        lines.append(f"Último erro registrado: {e[:200]}.")
    return " ".join(lines)
