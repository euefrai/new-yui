# ==========================================================
# YUI META-COGNITION LAYER
# Observador interno: analisa o próprio processo cognitivo.
# Sinais regulam planner, attention, identity — sem ifs espalhados.
# ==========================================================

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from core.energy_manager import get_energy_manager
except ImportError:
    get_energy_manager = None
try:
    from core.self_state import get_all as get_self_state
except ImportError:
    get_self_state = lambda: {}

# Histórico de ações (últimas N) — loop detector
ACTION_HISTORY: deque = deque(maxlen=20)
LOOP_THRESHOLD = 3
CONTEXT_OVERLOAD_THRESHOLD = 8
TOO_MANY_STEPS_THRESHOLD = 4
META_SCORE_SIMPLIFIED = 50


@dataclass
class MetaState:
    """Estado global para análise metacognitiva."""
    energy: float = 100.0
    context_size: int = 0
    steps_planned: int = 0
    steps_executed: int = 0
    current_goal: str = ""
    last_result_ok: bool = True
    last_error: str = ""


def record_action(action: str) -> None:
    """Registra ação executada (para loop detector)."""
    if action:
        ACTION_HISTORY.append(action)


def get_action_history() -> List[str]:
    """Retorna últimas ações."""
    return list(ACTION_HISTORY)


def _build_state(
    context_size: int = 0,
    steps_planned: int = 0,
    steps_executed: int = 0,
    current_goal: str = "",
) -> MetaState:
    """Monta estado a partir dos módulos globais."""
    energy = 100.0
    if get_energy_manager:
        try:
            energy = get_energy_manager().energy
        except Exception:
            pass

    self_state = get_self_state() or {}
    last_ok = not bool(self_state.get("last_error"))

    return MetaState(
        energy=energy,
        context_size=context_size,
        steps_planned=steps_planned,
        steps_executed=steps_executed,
        current_goal=current_goal,
        last_result_ok=last_ok,
        last_error=str(self_state.get("last_error", "")),
    )


def _detect_loop() -> bool:
    """Detecta se últimas ações são repetidas (ex: create_file x3)."""
    hist = list(ACTION_HISTORY)
    if len(hist) < LOOP_THRESHOLD:
        return False
    last = hist[-LOOP_THRESHOLD:]
    return len(set(last)) == 1


class MetaCognition:
    """
    Observador interno: analisa estado e emite sinais.
    Sinais influenciam planner, attention, identity.
    """

    def analyze(self, state: Optional[MetaState] = None, **kwargs) -> Dict[str, Any]:
        """
        Analisa estado e retorna sinais.
        kwargs: context_size, steps_planned, steps_executed, current_goal
        """
        if state is None:
            state = _build_state(**kwargs)

        signals: Dict[str, Any] = {}
        signals["low_energy"] = state.energy < 20
        signals["critical_energy"] = state.energy < 10
        signals["too_many_steps"] = (
            state.steps_planned > TOO_MANY_STEPS_THRESHOLD
            or state.steps_executed > TOO_MANY_STEPS_THRESHOLD
        )
        signals["context_overload"] = state.context_size > CONTEXT_OVERLOAD_THRESHOLD
        signals["loop_detected"] = _detect_loop()
        signals["last_failed"] = not state.last_result_ok

        meta_score = 100
        if signals["low_energy"]:
            meta_score -= 20
        if signals["critical_energy"]:
            meta_score -= 30
        if signals["loop_detected"]:
            meta_score -= 30
        if signals["context_overload"]:
            meta_score -= 15
        if signals["too_many_steps"]:
            meta_score -= 10
        if signals["last_failed"]:
            meta_score -= 10

        signals["meta_score"] = max(0, meta_score)
        signals["simplified_mode"] = signals["meta_score"] < META_SCORE_SIMPLIFIED

        return signals

    def check_redundant_action(
        self,
        tool_name: str,
        args: Optional[Dict[str, Any]] = None,
    ) -> tuple[bool, str]:
        """
        World Model: verifica se ação é redundante (ex: criar arquivo que já existe).
        Retorna (is_redundant, motivo).
        """
        try:
            from core.world_model import get_world_model
        except Exception:
            return False, ""

        if tool_name != "criar_projeto_arquivos":
            return False, ""

        wm = get_world_model()
        files = args.get("files") if args else []
        if not files:
            return False, ""

        root_dir = (args.get("root_dir") or "").replace("\\", "/")
        base = root_dir if "generated_projects" in root_dir else f"generated_projects/{root_dir}" if root_dir else ""
        existing = []
        for f in files:
            path = f.get("path", f) if isinstance(f, dict) else str(f)
            full_path = f"{base}/{path}".strip("/") if base else path
            if wm.file_exists(full_path) or wm.file_exists(path):
                existing.append(path)

        if existing:
            return True, f"Arquivos já existem no projeto: {', '.join(existing[:3])}"
        return False, ""


_meta: Optional[MetaCognition] = None


def get_metacognition() -> MetaCognition:
    """Retorna instância global do MetaCognition."""
    global _meta
    if _meta is None:
        _meta = MetaCognition()
    return _meta
