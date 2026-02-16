# ==========================================================
# YUI IDENTITY CORE
# Policy layer: regras estruturais, preferências de estratégia, limites internos.
# Existe no código, antes do planner — não é só prompt.
# ==========================================================

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from config import settings
    IDENTITY_STATE_PATH = Path(settings.DATA_DIR) / "identity_state.json"
except Exception:
    IDENTITY_STATE_PATH = Path(__file__).resolve().parents[1] / "data" / "identity_state.json"

# Tools que exigem risk_tolerance > low (ex: destrutivas, pesadas)
HEAVY_OR_RISKY_TOOLS = {"executar_comando", "deletar_arquivo", "apagar_arquivo", "mover_arquivo"}


def _load_state() -> Dict[str, Any]:
    """Carrega identity_state.json."""
    IDENTITY_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not IDENTITY_STATE_PATH.exists():
        return {}
    try:
        with open(IDENTITY_STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(data: Dict[str, Any]) -> None:
    """Salva identity_state.json."""
    import datetime
    IDENTITY_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    data["last_updated"] = datetime.datetime.utcnow().isoformat()
    with open(IDENTITY_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class IdentityCore:
    """
    Esqueleto da mente: decisões consistentes, previsibilidade estratégica.
    decision_style: pragmatic (menos etapas) | exploratory (mais etapas)
    risk_tolerance: low (evita tools pesadas) | medium | high
    response_depth: short | medium | long
    """

    def __init__(self):
        state = _load_state()
        self.decision_style = state.get("decision_style", "pragmatic")
        self.risk_tolerance = state.get("risk_tolerance", "low")
        self.response_depth = state.get("response_depth", "medium")
        self._learned: Dict[str, Any] = state.get("learned", {})

    def apply_energy_context(self, energy: Optional[float] = None) -> None:
        """
        Identity + Energy: energia baixa → response_depth = short.
        Modifica temporariamente para este turno.
        """
        if energy is not None and energy < 20:
            self.response_depth = "short"
        elif energy is not None and energy < 10:
            self.response_depth = "short"

    def get_effective_response_depth(self, energy: Optional[float] = None) -> str:
        """Retorna response_depth efetivo (considerando energia)."""
        if energy is not None and energy < 20:
            return "short"
        return self.response_depth

    def get_max_plan_steps(self) -> int:
        """Identity modula planner: pragmatic → menos etapas."""
        if self.decision_style == "pragmatic":
            return 4
        if self.decision_style == "exploratory":
            return 8
        return 6

    def is_tool_allowed(self, tool_name: str) -> bool:
        """
        Identity como filtro final: valida ação antes de executar.
        risk_tolerance low → bloqueia tools pesadas/destrutivas.
        """
        if self.risk_tolerance in ("medium", "high"):
            return True
        return tool_name not in HEAVY_OR_RISKY_TOOLS

    def validate(self, action: str, tool_name: Optional[str] = None, args: Optional[Dict] = None) -> tuple[bool, str]:
        """
        Valida ação antes de executar.
        Retorna (ok, motivo).
        """
        if tool_name and not self.is_tool_allowed(tool_name):
            return False, f"Identidade conservadora: ferramenta '{tool_name}' não permitida com risk_tolerance baixo."
        if tool_name and args:
            if tool_name in ("deletar_arquivo", "apagar_arquivo") and self.risk_tolerance == "low":
                return False, "Identidade conservadora: não apaga arquivos."
        return True, ""

    def learn(self, key: str, value: Any) -> None:
        """
        Identity Memory: aprende preferências (ex: respostas longas causam erro).
        Persiste em identity_state.json.
        """
        self._learned[key] = value
        state = _load_state()
        state["decision_style"] = self.decision_style
        state["risk_tolerance"] = self.risk_tolerance
        state["response_depth"] = self.response_depth
        state["learned"] = self._learned
        _save_state(state)

    def learn_from_error(self, error_type: str, context: Optional[Dict] = None) -> None:
        """
        Ajuste automático: se respostas longas causam erro, response_depth = short.
        """
        if error_type == "response_too_long" or (context and context.get("truncated")):
            self.response_depth = "short"
            self.learn("response_depth", "short")
            self.learn("learned_from", "response_too_long")


_identity_core: Optional[IdentityCore] = None


def get_identity_core() -> IdentityCore:
    """Retorna instância global do IdentityCore."""
    global _identity_core
    if _identity_core is None:
        _identity_core = IdentityCore()
    return _identity_core
