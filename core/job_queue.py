"""
YUI JOB QUEUE
API leve → fila → Worker processa em background.
Gerencia picos de carga e evita timeouts no Zeabur.
"""

import uuid
import time
import threading
from threading import Lock
from typing import Any, Dict, Optional

try:
    from core.task_scheduler import get_scheduler
except ImportError:
    get_scheduler = None

# Armazenamento em memória dos estados dos Jobs
_results: Dict[str, Dict[str, Any]] = {}
_lock = Lock()
TTL = 600  # 10 min (Tempo de vida dos resultados no cache para economizar RAM)

# Métricas globais para monitoramento administrativo
_metrics: Dict[str, int] = {
    "enqueued": 0,
    "done": 0,
    "failed": 0,
    "cleaned": 0,
}


def _run_job(payload: Dict[str, Any]) -> None:
    """Worker: executa a tarefa e armazena resultado."""
    job_id = payload.get("job_id")
    fn_name = payload.get("fn")
    args = payload.get("args", {})
    if not job_id or not fn_name:
        return

    try:
        # Atualmente focado no processamento de Chat via Agent Controller
        if fn_name == "agent_controller":
            from core.ai_loader import get_agent_controller
            agent = get_agent_controller()
            chunks = []
            for c in agent(
                args.get("user_id", ""),
                args.get("chat_id", ""),
                args.get("message", ""),
                model=args.get("model", "yui"),
            ):
                chunks.append(c)
            result = "".join(chunks).strip()
        else:
            result = None

        with _lock:
            _results[job_id] = {
                "status": "done",
                "result": result,
                "created_at": _results.get(job_id, {}).get("created_at", time.time()),
                "updated_at": time.time(),
            }
            _metrics["done"] += 1
    except Exception as e:
        with _lock:
            _results[job_id] = {
                "status": "failed",
                "error": str(e),
                "created_at": _results.get(job_id, {}).get("created_at", time.time()),
                "updated_at": time.time(),
            }
            _metrics["failed"] += 1


def enqueue_chat(
    user_id: str,
    chat_id: str,
    message: str,
    model: str = "yui",
) -> str:
    """Enfileira processamento de chat. Retorna job_id para o Poll do cliente."""
    cleanup_old_jobs()
    job_id = str(uuid.uuid4())[:12]
    payload = {
        "job_id": job_id,
        "fn": "agent_controller",
        "args": {"user_id": user_id, "chat_id": chat_id, "message": message, "model": model},
    }

    with _lock:
        _results[job_id] = {"status": "queued", "created_at": time.time(), "updated_at": time.time()}
        _metrics["enqueued"] += 1

    if get_scheduler and get_scheduler():
        get_scheduler().add(_run_job, payload, task_id=job_id)
    else:
        thread = threading.Thread(target=lambda: _run_job(payload), daemon=True)
        thread.start()

    return job_id


def get_job_result(job_id: str) -> Optional[Dict[str, Any]]:
    """Retorna status do job: {status: queued|done|failed, result?, error?}."""
    cleanup_old_jobs()
    with _lock:
        return _results.get(job_id)


def cleanup_old_jobs(ttl_seconds: Optional[int] = None) -> int:
    """Remove jobs expirados para economizar memória RAM (crucial para o Zeabur)."""
    ttl = int(ttl_seconds or TTL)
    if ttl <= 0:
        return 0
    now = time.time()
    with _lock:
        to_remove = []
        for j_id, data in _results.items():
            ts = data.get("updated_at") or data.get("created_at")
            if ts is None:
                continue
            if (now - float(ts)) > ttl:
                to_remove.append(j_id)
        for j_id in to_remove:
            _results.pop(j_id, None)
        removed = len(to_remove)
        _metrics["cleaned"] += removed
    return removed


def get_job_metrics() -> Dict[str, Any]:
    """Retorna estatísticas de uso da fila para observabilidade."""
    with _lock:
        queued = sum(1 for j in _results.values() if j.get("status") == "queued")
        running = sum(1 for j in _results.values() if j.get("status") == "running")
        return {
            "queued": queued,
            "running": running,
            "stored_results": len(_results),
            "enqueued_total": _metrics.get("enqueued", 0),
            "done_total": _metrics.get("done", 0),
            "failed_total": _metrics.get("failed", 0),
            "cleaned_total": _metrics.get("cleaned", 0),
            "ttl_seconds": TTL,
        }
