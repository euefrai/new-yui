# ==========================================================
# YUI TASK SCHEDULER
# Sistema de ações assíncronas — separa imediato vs fila vs background.
#
# Ações pesadas não disputam CPU com o chat.
# Yui responde → continua trabalhando em silêncio.
# ==========================================================

import threading
import uuid
from queue import Queue
from typing import Any, Callable, Optional

try:
    from core.event_bus import emit
except ImportError:
    emit = lambda e, *a, **k: None


class TaskScheduler:
    """
    Fila de tarefas em background. Sem Redis, Celery — só separação de fluxo.

    add(fn, data) → entra na fila
    add_now(fn, data) → executa em thread separada (não bloqueia)
    """

    def __init__(self, maxsize: int = 100):
        self._queue: Queue = Queue(maxsize=maxsize)
        self._worker_started = False
        self._lock = threading.Lock()

    def add(self, fn: Callable[..., Any], data: Any = None, task_id: Optional[str] = None) -> str:
        """
        Adiciona tarefa à fila. Executa em background.
        Retorna task_id para rastreamento.
        """
        tid = task_id or str(uuid.uuid4())[:8]
        self._ensure_worker()
        self._queue.put((fn, data, tid))
        emit("task_queued", task_id=tid, fn_name=getattr(fn, "__name__", "unknown"))
        return tid

    def add_now(self, fn: Callable[..., Any], data: Any = None) -> None:
        """
        Executa em thread separada imediatamente (não bloqueia).
        Para ações que devem rodar "agora" mas sem travar o fluxo principal.
        """
        def _run():
            try:
                fn(data) if data is not None else fn()
            except Exception:
                pass

        threading.Thread(target=_run, daemon=True).start()

    def _ensure_worker(self) -> None:
        with self._lock:
            if self._worker_started:
                return
            self._worker_started = True
            t = threading.Thread(target=self._worker, daemon=True)
            t.start()

    def _worker(self) -> None:
        while True:
            try:
                fn, data, task_id = self._queue.get()
                fn_name = getattr(fn, "__name__", "unknown")
                try:
                    from core.observability import trace
                    with trace(f"task_{fn_name}", meta={"task_id": task_id}):
                        result = fn(data) if data is not None else fn()
                    emit("task_done", task_id=task_id, result=result)
                except Exception as e:
                    emit("task_failed", task_id=task_id, error=str(e))
                finally:
                    self._queue.task_done()
            except Exception:
                pass

    def queue_size(self) -> int:
        """Tamanho atual da fila."""
        return self._queue.qsize()


_scheduler: Optional[TaskScheduler] = None


def get_scheduler() -> TaskScheduler:
    """Retorna o TaskScheduler singleton."""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler()
    return _scheduler
