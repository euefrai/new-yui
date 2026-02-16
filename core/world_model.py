# ==========================================================
# YUI WORLD MODEL
# Mapa do universo: o que existe, o que mudou, o que está ativo.
# Estado do ambiente — não memória de conversa.
# ==========================================================

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from config import settings
    WORLD_SNAPSHOT_PATH = Path(settings.DATA_DIR) / "world_snapshot.json"
except Exception:
    WORLD_SNAPSHOT_PATH = Path(__file__).resolve().parents[1] / "data" / "world_snapshot.json"


def _load_snapshot() -> Dict[str, Any]:
    """Carrega world_snapshot.json."""
    WORLD_SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not WORLD_SNAPSHOT_PATH.exists():
        return {}
    try:
        with open(WORLD_SNAPSHOT_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_snapshot(data: Dict[str, Any]) -> None:
    """Salva world_snapshot.json."""
    import datetime
    WORLD_SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    data["last_updated"] = datetime.datetime.utcnow().isoformat()
    with open(WORLD_SNAPSHOT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class WorldModel:
    """
    Mapa do ambiente da Yui.
    project: arquivos, pastas, último modificado
    runtime: energia, goal ativo, modo
    tasks: tarefas em andamento, última ação
    """

    def __init__(self):
        snap = _load_snapshot()
        self.project: Dict[str, Any] = snap.get("project", {
            "known_files": [],
            "main_folders": [],
            "last_modified": "",
            "root": "",
            "main_file": "",
        })
        self.runtime: Dict[str, Any] = snap.get("runtime", {
            "energy": 100.0,
            "active_goal": "",
            "mode": "manual",
        })
        self.tasks: List[Dict[str, Any]] = snap.get("tasks", [])

    def update_project(
        self,
        known_files: Optional[List[str]] = None,
        main_folders: Optional[List[str]] = None,
        root: Optional[str] = None,
        main_file: Optional[str] = None,
        last_modified: Optional[str] = None,
    ) -> None:
        """Atualiza estado do projeto."""
        if known_files is not None:
            self.project["known_files"] = known_files[:50]
        if main_folders is not None:
            self.project["main_folders"] = main_folders
        if root is not None:
            self.project["root"] = root
        if main_file is not None:
            self.project["main_file"] = main_file
        if last_modified is not None:
            self.project["last_modified"] = last_modified

    def update_runtime(
        self,
        energy: Optional[float] = None,
        active_goal: Optional[str] = None,
        mode: Optional[str] = None,
    ) -> None:
        """Atualiza estado de runtime."""
        if energy is not None:
            self.runtime["energy"] = energy
        if active_goal is not None:
            self.runtime["active_goal"] = active_goal
        if mode is not None:
            self.runtime["mode"] = mode

    def add_task(self, task: str, status: str = "in_progress") -> None:
        """Adiciona tarefa em andamento."""
        self.tasks.append({"task": task, "status": status})

    def set_last_action(self, action: str) -> None:
        """Registra última ação executada."""
        self.runtime["last_action"] = action

    def file_exists(self, path: str) -> bool:
        """Verifica se arquivo já existe no world model."""
        files = self.project.get("known_files", [])
        path_norm = path.replace("\\", "/")
        return any(path_norm in f or f.endswith(path) for f in files)

    def get_focus_hint(self) -> str:
        """Retorna hint para attention/planner (arquivo principal, etc.)."""
        main = self.project.get("main_file", "")
        root = self.project.get("root", "")
        if main:
            return f"Arquivo principal conhecido: {main}"
        if root:
            return f"Projeto em: {root}"
        return ""

    def to_dict(self) -> Dict[str, Any]:
        """Serializa para persistência."""
        return {
            "project": self.project,
            "runtime": self.runtime,
            "tasks": self.tasks[-10:],
        }

    def save(self) -> None:
        """Persiste snapshot no disco."""
        _save_snapshot(self.to_dict())

    def sync_from_modules(self) -> None:
        """Sincroniza runtime com energy, goals, etc."""
        try:
            from core.energy_manager import get_energy_manager
            self.runtime["energy"] = get_energy_manager().energy
        except Exception:
            pass
        try:
            from core.goals.goal_manager import get_active_goals
            goals = get_active_goals()
            self.runtime["active_goal"] = goals[0].name if goals else ""
        except Exception:
            pass

    def update_from_scan(self, raiz: str = ".") -> None:
        """Atualiza project state a partir de scan do filesystem."""
        try:
            from backend.ai.context_builder import listar_arquivos
            import os
            raiz_abs = os.path.abspath(raiz)
            files = listar_arquivos(raiz)
            rel_files = [os.path.relpath(f, raiz_abs) if raiz_abs else f for f in files]
            folders = list({str(Path(f).parent) for f in rel_files})[:15]
            main = ""
            for f in rel_files:
                if "main" in f.lower() or "app" in f.lower():
                    main = f
                    break
            if not main and rel_files:
                main = rel_files[0]
            self.update_project(
                known_files=rel_files,
                main_folders=folders,
                root=raiz_abs,
                main_file=main,
            )
        except Exception:
            pass


_world: Optional[WorldModel] = None


def get_world_model() -> WorldModel:
    """Retorna instância global do WorldModel."""
    global _world
    if _world is None:
        _world = WorldModel()
    return _world
