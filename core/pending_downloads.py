# ==========================================================
# YUI PENDING DOWNLOADS
# URLs de arquivos (ex: ZIP) gerados em background.
# Frontend pode fazer poll para saber quando está pronto.
# ==========================================================

import time
from collections import deque
from threading import Lock

# (url, timestamp) — mantém últimos 5 min, máx 50
_entries: deque = deque(maxlen=50)
_lock = Lock()
_TTL = 300  # 5 min


def add_ready(url: str) -> None:
    """Registra um download pronto (ex: ZIP criado pelo scheduler)."""
    with _lock:
        _entries.append((url.strip(), time.time()))


def get_recent(since: float | None = None) -> list[str]:
    """
    Retorna URLs prontas (dentro do TTL).
    Se since informado, só retorna as adicionadas após esse timestamp.
    """
    now = time.time()
    cutoff = now - _TTL
    with _lock:
        urls = [u for u, ts in _entries if ts > cutoff and (since is None or ts > since)]
    return list(dict.fromkeys(urls))  # preserve order, no duplicates
