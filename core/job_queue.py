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
            _results[job_id] = {"status": "done", "result": result}
    except Exception as e:
        with _lock:
            _results[job_id] = {"status": "failed", "error": str(e)}


def enqueue_chat(
    user_id: str,
    chat_id: str,
    message: str,
    model: str = "yui",
) -> str:
    """Enfileira processamento de chat. Retorna job_id."""
    job_id = str(uuid.uuid4())[:12]
    payload = {
        "job_id": job_id,
        "fn": "agent_controller",
        "args": {"user_id": user_id, "chat_id": chat_id, "message": message, "model": model},
    }
    with _lock:
        _results[job_id] = {"status": "queued"}
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
    with _lock:
        return _results.get(job_id)


def cleanup_old_jobs() -> int:
    """Remove jobs antigos. Retorna quantidade removida."""
    # TODO: implementar TTL se necessário
    return 0
