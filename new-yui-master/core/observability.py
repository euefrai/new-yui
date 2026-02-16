# ==========================================================
# YUI OBSERVABILITY LAYER
# Consciência interna do sistema — rastreamento de ações.
#
# Responde: "O que estou fazendo?", "Qual nó demorou mais?",
# "Por que a CPU subiu?", "Qual módulo consumiu RAM?"
#
# Conecta: Event Bus, Scheduler, Governor, Execution Graph.
# ==========================================================

import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Dict, List, Optional

# Store recent (últimos 5 min, max 100 spans)
_spans: deque = deque(maxlen=100)
_activity: deque = deque(maxlen=50)
_lock = Lock()
_TTL = 300  # 5 min


@dataclass
class Span:
    """Um span de execução: nome, duração, status."""
    name: str
    start_ts: float
    end_ts: Optional[float] = None
    status: str = "running"  # running, done, failed
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> Optional[float]:
        if self.end_ts is not None:
            return round((self.end_ts - self.start_ts) * 1000, 1)
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "meta": self.meta,
        }


@dataclass
class Activity:
    """Item de atividade do sistema (para UI)."""
    kind: str  # graph, task, governor, event
    label: str
    detail: str = ""
    ts: float = field(default_factory=time.time)


class Trace:
    """
    Trace de execução: mede tempo e registra no observability.
    Uso: with trace("zip_builder"): run_zip()
    """

    def __init__(self, name: str, meta: Optional[Dict[str, Any]] = None):
        self.name = name
        self.meta = meta or {}
        self._span: Optional[Span] = None

    def start(self) -> None:
        self._span = Span(name=self.name, start_ts=time.time(), meta=dict(self.meta))
        with _lock:
            _spans.append(self._span)

    def end(self, status: str = "done") -> None:
        if self._span:
            self._span.end_ts = time.time()
            self._span.status = status

    def __enter__(self) -> "Trace":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.end(status="failed" if exc_type else "done")
        return False


# ==========================================================
# API pública
# ==========================================================

def trace(name: str, meta: Optional[Dict[str, Any]] = None) -> Trace:
    """Cria um Trace para medir execução."""
    return Trace(name=name, meta=meta)


def record_span(name: str, duration_ms: float, status: str = "done", meta: Optional[Dict] = None) -> None:
    """Registra um span já concluído."""
    now = time.time()
    s = Span(name=name, start_ts=now - duration_ms / 1000, end_ts=now, status=status, meta=meta or {})
    with _lock:
        _spans.append(s)


def record_activity(kind: str, label: str, detail: str = "") -> None:
    """Registra atividade para o painel System Activity."""
    with _lock:
        _activity.append(Activity(kind=kind, label=label, detail=detail))


def get_timeline(limit: int = 20) -> List[Dict[str, Any]]:
    """Retorna os spans recentes (Execution Timeline)."""
    now = time.time()
    cutoff = now - _TTL
    with _lock:
        items = [s for s in _spans if s.start_ts > cutoff]
    # Últimos primeiro
    items = list(reversed(items))[:limit]
    return [s.to_dict() for s in items]


def get_system_activity(limit: int = 10) -> List[Dict[str, Any]]:
    """Retorna atividade recente para UI (System Activity)."""
    now = time.time()
    cutoff = now - _TTL
    with _lock:
        items = [a for a in _activity if a.ts > cutoff]
    items = list(reversed(items))[:limit]
    return [
        {"kind": a.kind, "label": a.label, "detail": a.detail, "ts": a.ts}
        for a in items
    ]


def get_observability_snapshot() -> Dict[str, Any]:
    """Snapshot completo para API."""
    return {
        "timeline": get_timeline(limit=30),
        "activity": get_system_activity(limit=15),
    }


# ==========================================================
# Wrappers para Event Bus, Scheduler, Governor
# (Listener/wiring — não modifica os módulos originais)
# ==========================================================

def wire_observability() -> None:
    """Registra listeners no Event Bus para auto-tracing."""
    try:
        from core.event_bus import on

        def _on_execution_node_start(node_name: str = "", **kwargs):
            record_activity("graph", f"Graph: {node_name}", "running")

        def _on_execution_node_done(node_name: str = "", **kwargs):
            record_activity("graph", f"Graph: {node_name}", "done")

        def _on_execution_node_failed(node_name: str = "", **kwargs):
            record_activity("graph", f"Graph: {node_name}", "failed")

        def _on_task_queued(task_id: str = "", fn_name: str = "", **kwargs):
            record_activity("task", fn_name or task_id, "queued")

        def _on_task_done(task_id: str = "", **kwargs):
            record_activity("task", task_id, "done")

        def _on_task_failed(task_id: str = "", **kwargs):
            record_activity("task", task_id, "failed")

        def _on_memory_update_requested(**kwargs):
            record_activity("event", "Memory Update", "queued")

        def _on_zip_ready(download_url: str = "", **kwargs):
            record_activity("event", "ZIP Ready", download_url or "")

        def _on_workspace_toggled(open: bool = False, **kwargs):
            record_activity("event", "Workspace", "opened" if open else "closed")

        def _on_task_iniciada(task: str = "", **kwargs):
            record_activity("task", task or "unknown", "started")

        def _on_erro_detectado(source: str = "", error: str = "", **kwargs):
            record_activity("event", f"Erro ({source})", (error or "")[:80])

        def _on_memoria_alta(ram_mb: float = 0, threshold: float = 0, **kwargs):
            record_activity("event", "Memória alta", f"RAM {ram_mb:.0f}MB > {threshold:.0f}MB")

        on("execution_node_start", _on_execution_node_start)
        on("execution_node_done", _on_execution_node_done)
        on("execution_node_failed", _on_execution_node_failed)
        on("task_queued", _on_task_queued)
        on("task_done", _on_task_done)
        on("task_failed", _on_task_failed)
        on("memory_update_requested", _on_memory_update_requested)
        on("zip_ready", _on_zip_ready)
        on("workspace_toggled", _on_workspace_toggled)
        on("task_iniciada", _on_task_iniciada)
        on("erro_detectado", _on_erro_detectado)
        on("memoria_alta", _on_memoria_alta)
    except Exception:
        pass


def record_governor_decision(feature: str, allow: bool, reason: str) -> None:
    """Chamado pelo Governor (ou wrapper) quando decide."""
    label = f"Governor: {feature}"
    detail = "blocked" if not allow else "ok"
    if not allow:
        detail = reason
    record_activity("governor", label, detail)
