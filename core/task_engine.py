# ==========================================================
# YUI TASK ENGINE — Cérebro Operacional
#
# Em vez de if comando == "editar_arquivo": editar()
# você passa a ter: task_engine.executar("editar_arquivo", dados)
#
# Permite:
# - Heathcliff planejar várias ações
# - Logar custo por tarefa
# - Limitar RAM por tipo de ação
# - UI: "🟡 Heathcliff está editando 3 arquivos..."
# ==========================================================

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

try:
    from core.event_bus import emit
except ImportError:
    emit = lambda e, *a, **k: None


def _emit_task_finished(info: TaskInfo) -> None:
    """Emite task_finished para Reflection Loop (telemetria pós-execução)."""
    duration = (info.ended_at or time.time()) - info.started_at
    success = info.status == "done"
    emit(
        "task_finished",
        task_id=info.id,
        task_type=info.tipo,
        duration=duration,
        success=success,
        error=info.error,
        meta=info.meta,
    )


@dataclass
class TaskInfo:
    """Status de uma tarefa em execução ou recente."""
    id: str
    tipo: str
    status: str  # pending | running | done | failed
    started_at: float
    ended_at: Optional[float] = None
    meta: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


TaskFn = Callable[..., Any]


class TaskEngine:
    """
    Registry e executor de tarefas executáveis.
    Cérebro operacional da Yui — tudo vira task.
    """

    def __init__(self, max_active: int = 50):
        self._tasks: Dict[str, TaskFn] = {}
        self._active: Dict[str, TaskInfo] = {}
        self._recent: List[TaskInfo] = []
        self._max_active = max_active
        self._max_recent = 20

    def registrar(self, nome: str, func: TaskFn) -> None:
        """Registra uma tarefa pelo nome."""
        self._tasks[nome] = func

    def listar(self) -> List[str]:
        """Retorna nomes de todas as tarefas registradas."""
        return list(self._tasks.keys())

    def executar(
        self,
        nome: str,
        *args: Any,
        task_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        """
        Executa uma tarefa pelo nome.

        Raises:
            ValueError: se tarefa não encontrada.
        """
        if nome not in self._tasks:
            raise ValueError(f"Tarefa '{nome}' não encontrada.")

        tid = task_id or f"task_{uuid.uuid4().hex[:12]}"
        fn = self._tasks[nome]
        info = TaskInfo(
            id=tid,
            tipo=nome,
            status="running",
            started_at=time.time(),
            meta=meta or {},
        )
        self._active[tid] = info
        self._prune_active()

        emit("task_queued", task_id=tid, fn_name=nome)
        emit("task_iniciada", task=nome, task_id=tid, fn_name=nome)
        try:
            try:
                from core.execution_guard import get_guard
                get_guard().wait_if_needed()
            except Exception:
                pass
            result = fn(*args, **kwargs)
            info.status = "done"
            info.ended_at = time.time()
            emit("task_done", task_id=tid, result=result)
            return result
        except Exception as e:
            info.status = "failed"
            info.ended_at = time.time()
            info.error = str(e)
            emit("task_failed", task_id=tid, error=str(e))
            emit("erro_detectado", source="task_engine", error=str(e), task_id=tid, task_type=nome)
            raise
        finally:
            self._move_to_recent(info)
            self._active.pop(tid, None)
            _emit_task_finished(info)

    def executar_tool(self, tool_name: str, args: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        """
        Executa uma tool registrada via run_tool, com rastreamento de task.
        Retorno: { ok, result, error } — igual ao tool_runner.
        """
        from core.tool_runner import run_tool
        tid = f"tool_{uuid.uuid4().hex[:8]}"
        info = TaskInfo(
            id=tid,
            tipo=_tool_to_tipo(tool_name),
            status="running",
            started_at=time.time(),
            meta={"tool": tool_name, "args_keys": list((args or {}).keys())},
        )
        self._active[tid] = info
        self._prune_active()

        emit("task_queued", task_id=tid, fn_name=tool_name)
        emit("task_iniciada", task=_tool_to_tipo(tool_name), task_id=tid, fn_name=tool_name)
        try:
            try:
                from core.execution_guard import get_guard
                get_guard().wait_if_needed()
            except Exception:
                pass
            out = run_tool(tool_name, args or {})
            info.status = "done"
            info.ended_at = time.time()
            emit("task_done", task_id=tid, result=out)
            return out
        except Exception as e:
            info.status = "failed"
            info.ended_at = time.time()
            info.error = str(e)
            emit("task_failed", task_id=tid, error=str(e))
            emit("erro_detectado", source="task_engine", error=str(e), task_id=tid, task_type=tool_name)
            return {"ok": False, "result": None, "error": str(e)}
        finally:
            self._move_to_recent(info)
            self._active.pop(tid, None)
            _emit_task_finished(info)

    def _prune_active(self) -> None:
        """Limita tarefas ativas e recentes."""
        if len(self._active) > self._max_active:
            oldest = sorted(self._active.items(), key=lambda x: x[1].started_at)[: len(self._active) - self._max_active]
            for k, _ in oldest:
                self._active.pop(k, None)

    def _move_to_recent(self, info: TaskInfo) -> None:
        self._recent.insert(0, info)
        self._recent = self._recent[: self._max_recent]

    def get_active(self) -> List[Dict[str, Any]]:
        """Retorna tarefas em execução (para UI)."""
        return [_task_info_to_dict(t) for t in self._active.values()]

    def get_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retorna tarefas recentes (done/failed)."""
        return [_task_info_to_dict(t) for t in self._recent[:limit]]

    def get_summary(self) -> Dict[str, Any]:
        """
        Resumo para UI: "Heathcliff está editando 3 arquivos..."
        {
          "active_count": 2,
          "active": [{"id","tipo","status","meta"}],
          "summary_text": "editando 2 arquivos, gerando ZIP"
        }
        """
        active = self.get_active()
        by_tipo: Dict[str, int] = {}
        for t in active:
            tipo = t.get("tipo", "unknown")
            by_tipo[tipo] = by_tipo.get(tipo, 0) + 1

        parts = []
        for tipo, count in sorted(by_tipo.items(), key=lambda x: -x[1]):
            label = _tipo_to_label(tipo)
            if count == 1:
                parts.append(label)
            else:
                parts.append(f"{label} ({count})")

        return {
            "active_count": len(active),
            "active": active,
            "by_tipo": by_tipo,
            "summary_text": ", ".join(parts) if parts else "",
        }


def _task_info_to_dict(info: TaskInfo) -> Dict[str, Any]:
    return {
        "id": info.id,
        "tipo": info.tipo,
        "status": info.status,
        "started_at": info.started_at,
        "ended_at": info.ended_at,
        "meta": info.meta,
        "error": info.error,
    }


def _tool_to_tipo(tool_name: str) -> str:
    """Mapeia nome da tool para tipo legível."""
    m = {
        "fs_create_file": "editar_codigo",
        "fs_create_folder": "editar_codigo",
        "fs_delete_file": "editar_codigo",
        "criar_projeto_arquivos": "criar_projeto",
        "criar_zip_projeto": "gerar_zip",
        "analisar_projeto": "analisar_projeto",
        "analisar_arquivo": "analisar_arquivo",
        "observar_ambiente": "observar_ambiente",
        "consultar_indice_projeto": "consultar_indice",
        "buscar_web": "buscar_web",
        "get_current_time": "get_time",
        "generate_project_map": "gerar_mapa",
        "create_mission": "criar_missao",
        "update_mission_progress": "atualizar_missao",
    }
    return m.get(tool_name, tool_name)


def _tipo_to_label(tipo: str) -> str:
    """Converte tipo para texto amigável."""
    labels = {
        "editar_codigo": "editando arquivo(s)",
        "criar_projeto": "criando projeto",
        "gerar_zip": "gerando ZIP",
        "analisar_projeto": "analisando projeto",
        "analisar_arquivo": "analisando arquivo",
        "observar_ambiente": "observando ambiente",
        "consultar_indice": "consultando índice",
        "buscar_web": "buscando na web",
        "get_time": "obtendo horário",
        "gerar_mapa": "gerando mapa",
        "criar_missao": "criando missão",
        "atualizar_missao": "atualizando missão",
    }
    return labels.get(tipo, tipo)


# --- Singleton ---
_engine: Optional[TaskEngine] = None


def get_task_engine() -> TaskEngine:
    """Retorna o TaskEngine singleton."""
    global _engine
    if _engine is None:
        _engine = TaskEngine()
        _load_capabilities(_engine)
    return _engine


def _load_capabilities(engine: TaskEngine) -> None:
    """
    Carrega capabilities dinamicamente (core/capabilities/cap_*.py).
    Fallback: _bootstrap_tasks se nenhuma capability carregar.
    """
    try:
        from core.capability_loader import carregar_capabilities
        loaded = carregar_capabilities(engine)
        if loaded:
            return
    except Exception:
        pass
    _bootstrap_tasks(engine)


def _bootstrap_tasks(engine: TaskEngine) -> None:
    """
    Fallback: registra tarefas quando capabilities não carregam.
    """
    from core.tool_runner import run_tool

    def _wrap_tool(name: str):
        def _run(*args, **kwargs):
            d = kwargs if kwargs else (args[0] if args and isinstance(args[0], dict) else {})
            return run_tool(name, d)
        return _run

    for tool in [
        "fs_create_file",
        "fs_create_folder",
        "fs_delete_file",
        "criar_projeto_arquivos",
        "criar_zip_projeto",
        "analisar_projeto",
        "analisar_arquivo",
        "observar_ambiente",
        "consultar_indice_projeto",
        "buscar_web",
        "get_current_time",
        "generate_project_map",
        "create_mission",
        "update_mission_progress",
    ]:
        engine.registrar(tool, _wrap_tool(tool))
