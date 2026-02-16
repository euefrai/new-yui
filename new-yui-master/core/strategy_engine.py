# ==========================================================
# YUI STRATEGY ENGINE
# Decide COMO pensar antes de planejar.
# Não executa tools — só escolhe modo mental.
# ==========================================================

import json
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from config import settings
    STRATEGY_STATE_PATH = Path(settings.DATA_DIR) / "strategy_state.json"
except Exception:
    STRATEGY_STATE_PATH = Path(__file__).resolve().parents[1] / "data" / "strategy_state.json"

# Estratégias disponíveis
STRATEGY_EXPLORATION = "exploration"   # testar ideias novas
STRATEGY_FOCUSED = "focused"           # executar objetivo direto
STRATEGY_CORRECTION = "correction"     # corrigir erro ou bug
STRATEGY_MINIMAL = "minimal"           # modo leve (economia RAM)

# max_steps por estratégia
STRATEGY_MAX_STEPS = {
    STRATEGY_MINIMAL: 1,
    STRATEGY_CORRECTION: 2,
    STRATEGY_FOCUSED: 3,
    STRATEGY_EXPLORATION: 5,
}

# attention.top por estratégia
STRATEGY_ATTENTION_TOP = {
    STRATEGY_MINIMAL: 3,
    STRATEGY_FOCUSED: 5,
    STRATEGY_CORRECTION: 4,
    STRATEGY_EXPLORATION: 8,
}


def _load_state() -> Dict[str, Any]:
    """Carrega strategy_state.json."""
    STRATEGY_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not STRATEGY_STATE_PATH.exists():
        return {}
    try:
        with open(STRATEGY_STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(data: Dict[str, Any]) -> None:
    """Salva strategy_state.json."""
    import datetime
    STRATEGY_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    data["last_updated"] = datetime.datetime.utcnow().isoformat()
    with open(STRATEGY_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class StrategyEngine:
    """
    Cérebro que escolhe como pensar.
    Recebe estado (meta, energy, goals) e retorna estratégia.
    """

    def __init__(self):
        state = _load_state()
        self._last_strategy = state.get("last_strategy", "")
        self._fail_count = state.get("fail_count", 0)
        self._last_result = state.get("last_result", "")

    def choose(
        self,
        meta_signals: Optional[Dict[str, Any]] = None,
        energy: Optional[float] = None,
        goal_priority: float = 0,
        has_error: bool = False,
    ) -> str:
        """
        Escolhe estratégia baseado no estado.
        MetaCognition sugere correction quando exploration falhou.
        """
        meta = meta_signals or {}

        if meta.get("loop_detected") or meta.get("last_failed"):
            return STRATEGY_CORRECTION

        if energy is not None and energy < 20:
            return STRATEGY_MINIMAL

        if energy is not None and energy < 10:
            return STRATEGY_MINIMAL

        if meta.get("simplified_mode"):
            return STRATEGY_MINIMAL

        if goal_priority > 0.7 and not meta.get("context_overload"):
            return STRATEGY_FOCUSED

        if has_error and self._last_strategy == STRATEGY_EXPLORATION:
            return STRATEGY_CORRECTION

        return STRATEGY_EXPLORATION

    def get_max_steps(self, strategy: str) -> int:
        """Retorna max_steps para a estratégia."""
        return STRATEGY_MAX_STEPS.get(strategy, 5)

    def get_attention_top(self, strategy: str) -> int:
        """Retorna attention.top para a estratégia."""
        return STRATEGY_ATTENTION_TOP.get(strategy, 5)

    def record_result(self, strategy: str, success: bool) -> None:
        """Registra resultado para adaptação futura."""
        self._last_strategy = strategy
        self._last_result = "ok" if success else "fail"
        if not success:
            self._fail_count += 1
        else:
            self._fail_count = 0
        self._persist()

    def _persist(self) -> None:
        """Persiste estado."""
        _save_state({
            "last_strategy": self._last_strategy,
            "fail_count": self._fail_count,
            "last_result": self._last_result,
        })

    def sync_to_world_model(self) -> None:
        """Sincroniza last_strategy com World Model."""
        try:
            from core.world_model import get_world_model
            wm = get_world_model()
            wm.runtime["last_strategy"] = self._last_strategy
        except Exception:
            pass


_strategy_engine: Optional[StrategyEngine] = None


def get_strategy_engine() -> StrategyEngine:
    """Retorna instância global do StrategyEngine."""
    global _strategy_engine
    if _strategy_engine is None:
        _strategy_engine = StrategyEngine()
    return _strategy_engine
