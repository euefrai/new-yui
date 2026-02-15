# ==========================================================
# YUI JOB QUEUE
# API leve → fila → Worker processa em background.
#
# Quando USE_ASYNC_QUEUE=true, POST /send?async=1 retorna job_id.
# Client faz poll em GET /chat/job/{job_id} até ter resultado.
#
# Reduz picos de RAM na API; processamento pesado no worker.
# ==========================================================

import uuid
import time
from threading import Lock
from typing import Any, Callable, Dict, Optional

try:
    from core.task_scheduler import get_scheduler
except ImportError:
    get_scheduler = None

_results: Dict[str, Dict[str, Any]] = {}
_lock = Lock()
TTL = 600  # 10 min


def _run_job(payload: Dict[str, Any]) -> None:
    """Worker: executa a tarefa e armazena resultado."""
    job_id = payload.get("job_id")
    fn_name = payload.get("fn")
    args = payload.get("args", {})
    if not job_id or not fn_name:
        return
    try:
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
            _results[job_id] = {"status": "done", "result": result, "created_at": _results.get(job_id, {}).get("created_at", time.time()), "updated_at": time.time()}
    except Exception as e:
        with _lock:
            _results[job_id] = {"status": "failed", "error": str(e), "created_at": _results.get(job_id, {}).get("created_at", time.time()), "updated_at": time.time()}


def enqueue_chat(
    user_id: str,
    chat_id: str,
    message: str,
    model: str = "yui",
) -> str:
    """Enfileira processamento de chat. Retorna job_id."""
    cleanup_old_jobs()
    job_id = str(uuid.uuid4())[:12]
    payload = {
        "job_id": job_id,
        "fn": "agent_controller",
        "args": {"user_id": user_id, "chat_id": chat_id, "message": message, "model": model},
    }
    with _lock:
        _results[job_id] = {"status": "queued", "created_at": time.time(), "updated_at": time.time()}
    if get_scheduler:
        get_scheduler().add(_run_job, payload, task_id=job_id)
    else:
        # fallback: executa em thread
        import threading
        def _run():
            _run_job(payload)
        threading.Thread(target=_run, daemon=True).start()
    return job_id


def get_job_result(job_id: str) -> Optional[Dict[str, Any]]:
    """Retorna status do job: {status: queued|done|failed, result?, error?}."""
    cleanup_old_jobs()
    with _lock:
        return _results.get(job_id)


def cleanup_old_jobs(ttl_seconds: Optional[int] = None) -> int:
    """Remove jobs antigos. Retorna quantidade removida."""
    ttl = int(ttl_seconds or TTL)
    if ttl <= 0:
        return 0
    now = time.time()
    removed = 0
    with _lock:
        to_remove = []
        for job_id, data in _results.items():
            ts = data.get("updated_at") or data.get("created_at")
            if ts is None:
                continue
            if (now - float(ts)) > ttl:
                to_remove.append(job_id)
        for job_id in to_remove:
            _results.pop(job_id, None)
        removed = len(to_remove)
    return removed
