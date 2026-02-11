# ==========================================================
# YUI GOAL MANAGER
# Objetivos persistentes: a Yui deixa de viver só na mensagem atual.
# Goal decide direção, NUNCA executa tools — quem executa é o executor.
# ==========================================================

import datetime
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# Goals não usados há mais de N horas sofrem decay de prioridade
STALE_GOAL_HOURS = 48
STALE_GOAL_DECAY = 0.5

try:
    from config import settings
    GOAL_MEMORY_PATH = Path(settings.DATA_DIR) / "goal_memory.json"
except Exception:
    GOAL_MEMORY_PATH = Path(__file__).resolve().parents[2] / "data" / "goal_memory.json"


class GoalType(str, Enum):
    """Tipos de objetivo: priorização automática pelo planner."""
    SYSTEM_GOAL = "system"        # manter estabilidade, evitar erros
    USER_GOAL = "user"            # criar site, corrigir bug (pedido do usuário)
    SELF_IMPROVEMENT = "self"     # otimizar respostas, organizar memória


@dataclass
class Goal:
    """Objetivo persistente: nome, prioridade, status, tipo."""
    name: str
    priority: float = 1.0
    status: str = "active"
    goal_type: GoalType = GoalType.USER_GOAL
    progress: float = 0.0
    last_execution: str = ""
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["goal_type"] = self.goal_type.value
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Goal":
        goal_type = GoalType(d.get("goal_type", "user"))
        return cls(
            name=d.get("name", ""),
            priority=float(d.get("priority", 1.0)),
            status=d.get("status", "active"),
            goal_type=goal_type,
            progress=float(d.get("progress", 0.0)),
            last_execution=d.get("last_execution", ""),
            created_at=d.get("created_at", ""),
        )


def _load_memory() -> Dict[str, Any]:
    """Carrega goal_memory.json."""
    GOAL_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not GOAL_MEMORY_PATH.exists():
        return {"goals": [], "last_updated": ""}
    try:
        with open(GOAL_MEMORY_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"goals": [], "last_updated": ""}


def _save_memory(data: Dict[str, Any]) -> None:
    """Salva goal_memory.json."""
    GOAL_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    import datetime
    data["last_updated"] = datetime.datetime.utcnow().isoformat()
    with open(GOAL_MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _decay_stale_goals(goals: List[Goal]) -> None:
    """Attention nos Goals: objetivos não usados há muito tempo perdem prioridade."""
    now = datetime.datetime.utcnow()
    for g in goals:
        if not g.last_execution:
            continue
        try:
            last = datetime.datetime.fromisoformat(g.last_execution.replace("Z", "")[:19])
            if last.tzinfo:
                last = last.replace(tzinfo=None)
            delta_hours = (now - last).total_seconds() / 3600
            if delta_hours > STALE_GOAL_HOURS:
                g.priority = max(0.1, g.priority - STALE_GOAL_DECAY)
        except Exception:
            pass


def get_active_goals(user_id: str = "", chat_id: str = "", energy: Optional[float] = None) -> List[Goal]:
    """
    Retorna objetivos ativos, ordenados por prioridade (maior primeiro).
    Energy-aware: energia < 20 → ignora goals com prioridade baixa (< 0.5).
    Attention-aware: goals não usados há 48h+ têm prioridade reduzida.
    """
    data = _load_memory()
    all_goals = [Goal.from_dict(g) for g in data.get("goals", [])]
    active_goals = [g for g in all_goals if g.status == "active"]
    _decay_stale_goals(active_goals)
    if active_goals:
        data["goals"] = [g.to_dict() for g in all_goals]
        _save_memory(data)
    goals = active_goals
    if energy is not None and energy < 20:
        goals = [g for g in goals if g.priority >= 0.5]
    type_order = {GoalType.SYSTEM_GOAL: 0, GoalType.USER_GOAL: 1, GoalType.SELF_IMPROVEMENT: 2}
    goals.sort(key=lambda g: (-type_order.get(g.goal_type, 1), -g.priority))
    return goals


def add_goal(
    name: str,
    priority: float = 1.0,
    goal_type: GoalType = GoalType.USER_GOAL,
    user_id: str = "",
    chat_id: str = "",
) -> Goal:
    """Adiciona um objetivo ativo."""
    import datetime
    goal = Goal(
        name=name,
        priority=priority,
        status="active",
        goal_type=goal_type,
        progress=0.0,
        last_execution="",
        created_at=datetime.datetime.utcnow().isoformat(),
    )
    data = _load_memory()
    goals = [Goal.from_dict(g) for g in data.get("goals", [])]
    goals.append(goal)
    data["goals"] = [g.to_dict() for g in goals]
    _save_memory(data)
    return goal


def update_progress(
    goal_name: str,
    success: bool,
    delta: float = 0.1,
) -> None:
    """
    Micro reflexão: atualiza progresso após execução.
    success=True → aumenta progresso
    success=False → diminui prioridade (evita repetir estratégia que falhou)
    """
    data = _load_memory()
    import datetime
    now = datetime.datetime.utcnow().isoformat()
    goals = [Goal.from_dict(g) for g in data.get("goals", [])]
    for g in goals:
        if g.name == goal_name and g.status == "active":
            g.last_execution = now
            if success:
                g.progress = min(1.0, g.progress + delta)
            else:
                g.priority = max(0.1, g.priority - delta * 2)
            break
    data["goals"] = [g.to_dict() for g in goals]
    _save_memory(data)


def complete_goal(goal_name: str) -> None:
    """Marca objetivo como concluído."""
    data = _load_memory()
    goals = [Goal.from_dict(g) for g in data.get("goals", [])]
    for g in goals:
        if g.name == goal_name:
            g.status = "completed"
            break
    data["goals"] = [g.to_dict() for g in goals]
    _save_memory(data)


def goals_to_context(goals: List[Goal]) -> str:
    """Converte goals para texto injetável no prompt do planner."""
    if not goals:
        return ""
    lines = ["Objetivos ativos (considere ao planejar):"]
    for g in goals[:5]:
        lines.append(f"  - [{g.goal_type.value}] {g.name} (prioridade={g.priority:.1f}, progresso={g.progress:.0%})")
    return "\n".join(lines)
