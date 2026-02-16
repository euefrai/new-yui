"""
Project Brain — Engine de Missões
Objetivos persistentes: a IA deixa de reagir e passa a agir com continuidade.
input -> project_brain (missão ativa) -> planner -> executor
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from config import settings
    MISSION_PATH = Path(settings.DATA_DIR) / "missions.json"
except Exception:
    MISSION_PATH = Path(__file__).resolve().parents[1] / "data" / "missions.json"


@dataclass
class Mission:
    """Missão persistente: projeto, objetivo, status, tarefas."""
    project: str
    goal: str
    status: str = "in_progress"  # in_progress, completed, paused
    tasks: List[str] = field(default_factory=list)
    current_task: str = ""
    progress: float = 0.0
    created_at: str = ""
    updated_at: str = ""
    user_id: str = ""
    chat_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Mission":
        return cls(
            project=d.get("project", ""),
            goal=d.get("goal", ""),
            status=d.get("status", "in_progress"),
            tasks=list(d.get("tasks", [])),
            current_task=d.get("current_task", ""),
            progress=float(d.get("progress", 0.0)),
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
            user_id=d.get("user_id", ""),
            chat_id=d.get("chat_id", ""),
        )


def _load() -> Dict[str, Any]:
    MISSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not MISSION_PATH.exists():
        return {"missions": [], "active_id": None}
    try:
        with open(MISSION_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"missions": [], "active_id": None}


def _save(data: Dict[str, Any]) -> None:
    MISSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MISSION_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_active_mission(user_id: str = "", chat_id: str = "") -> Optional[Mission]:
    """Retorna missão ativa. Prioriza user_id/chat_id."""
    data = _load()
    missions = [Mission.from_dict(m) for m in data.get("missions", [])]
    active_id = data.get("active_id")
    for m in missions:
        if m.status != "in_progress":
            continue
        if active_id and m.project == active_id:
            return m
        if user_id and m.user_id and m.user_id != user_id:
            continue
        if chat_id and m.chat_id and m.chat_id != chat_id:
            continue
        return m
    return missions[0] if missions and missions[0].status == "in_progress" else None


def create_mission(
    project: str,
    goal: str,
    tasks: Optional[List[str]] = None,
    user_id: str = "",
    chat_id: str = "",
) -> Mission:
    """Cria nova missão ativa."""
    now = datetime.utcnow().isoformat()
    mission = Mission(
        project=project,
        goal=goal,
        status="in_progress",
        tasks=tasks or [],
        current_task=tasks[0] if tasks else "",
        progress=0.0,
        created_at=now,
        updated_at=now,
        user_id=user_id,
        chat_id=chat_id,
    )
    data = _load()
    missions = [Mission.from_dict(m) for m in data.get("missions", [])]
    missions.append(mission)
    data["missions"] = [m.to_dict() for m in missions[-20:]]
    data["active_id"] = project
    _save(data)
    return mission


def update_mission_progress(
    project: str,
    task_completed: Optional[str] = None,
    progress_delta: float = 0.0,
    current_task: Optional[str] = None,
) -> bool:
    """Atualiza progresso da missão. Chamado após execução bem-sucedida."""
    data = _load()
    missions = [Mission.from_dict(m) for m in data.get("missions", [])]
    updated = False
    for m in missions:
        if m.project == project and m.status == "in_progress":
            if task_completed and task_completed in m.tasks:
                m.tasks = [t for t in m.tasks if t != task_completed]
            if progress_delta:
                m.progress = min(1.0, m.progress + progress_delta)
            if current_task is not None:
                m.current_task = current_task
            m.updated_at = datetime.utcnow().isoformat()
            if not m.tasks and m.progress >= 1.0:
                m.status = "completed"
            updated = True
            break
    if updated:
        data["missions"] = [m.to_dict() for m in missions]
        _save(data)
    return updated


def complete_mission(project: str) -> bool:
    """Marca missão como concluída."""
    data = _load()
    missions = [Mission.from_dict(m) for m in data.get("missions", [])]
    for m in missions:
        if m.project == project:
            m.status = "completed"
            m.progress = 1.0
            m.updated_at = datetime.utcnow().isoformat()
            data["missions"] = [m.to_dict() for m in missions]
            data["active_id"] = None
            _save(data)
            return True
    return False


def mission_to_prompt(mission: Mission) -> str:
    """Converte missão para texto injetável no prompt (Project Brain)."""
    if not mission or mission.status != "in_progress":
        return ""
    pct = int(mission.progress * 100)
    lines = [
        "[MISSÃO ATIVA — Project Brain]",
        f"Projeto: {mission.project}",
        f"Objetivo: {mission.goal}",
        f"Progresso: {pct}%",
    ]
    if mission.current_task:
        lines.append(f"Próxima ação: {mission.current_task}")
    if mission.tasks:
        lines.append("Tarefas pendentes:")
        for t in mission.tasks[:8]:
            lines.append(f"  - {t}")
    lines.append("")
    lines.append("Considere esta missão ao responder. Avance uma tarefa por vez. Após concluir, atualize o progresso.")
    return "\n".join(lines)
