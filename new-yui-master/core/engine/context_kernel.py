"""
Context Kernel — Unifica todo o contexto em tempo real.

Arquivos ativos + erros do console + histórico do chat + estado do workspace.

Permite que Heathcliff entenda o projeto em tempo real.
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from config.settings import SANDBOX_DIR, BASE_DIR
except Exception:
    SANDBOX_DIR = Path(__file__).resolve().parents[2] / "sandbox"
    BASE_DIR = Path(__file__).resolve().parents[2]

_WORKSPACE_FILES_CACHE: List[str] = []
_WORKSPACE_FILES_CACHE_TS = 0.0
_WORKSPACE_CACHE_SEC = 30.0  # 30s para reduzir CPU (evita rglob frequente)


@dataclass
class ContextSnapshot:
    """Snapshot unificado do contexto do projeto."""
    active_files: List[str] = field(default_factory=list)
    workspace_files: List[str] = field(default_factory=list)
    console_errors: List[str] = field(default_factory=list)
    last_stdout: str = ""
    last_stderr: str = ""
    chat_summary: str = ""
    workspace_state: str = ""  # ex: "3 arquivos modificados"
    sandbox_path: str = ""


def _get_workspace_files() -> List[str]:
    """Lista itens no sandbox (apenas nível raiz — iterdir, não rglob). Cache 30s para reduzir CPU."""
    global _WORKSPACE_FILES_CACHE, _WORKSPACE_FILES_CACHE_TS
    now = time.time()
    if now - _WORKSPACE_FILES_CACHE_TS < _WORKSPACE_CACHE_SEC:
        return _WORKSPACE_FILES_CACHE
    try:
        sandbox = Path(SANDBOX_DIR)
        if not sandbox.is_dir():
            _WORKSPACE_FILES_CACHE = []
            _WORKSPACE_FILES_CACHE_TS = now
            return []
        ignore = {"__pycache__", ".git", "node_modules", ".venv", "venv", ".yui_map.json"}
        out: List[str] = []
        for p in sandbox.iterdir():
            if p.name in ignore or (p.name.startswith(".") and p.name not in (".env", ".env.example")):
                continue
            out.append(str(p.relative_to(sandbox)).replace("\\", "/") + ("/" if p.is_dir() else ""))
        _WORKSPACE_FILES_CACHE = sorted(out)[:80]
        _WORKSPACE_FILES_CACHE_TS = now
        return _WORKSPACE_FILES_CACHE
    except Exception:
        return _WORKSPACE_FILES_CACHE


def get_context_snapshot(
    user_id: str = "",
    chat_id: str = "",
    active_files: Optional[List[str]] = None,
    console_errors: Optional[List[str]] = None,
    last_stdout: str = "",
    last_stderr: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> ContextSnapshot:
    """
    Monta snapshot unificado do contexto.

    Args:
        user_id, chat_id: sessão
        active_files: arquivos abertos no editor (enviados pelo frontend)
        console_errors: erros do console (enviados pelo frontend)
        last_stdout, last_stderr: última execução
        extra: dados extras

    Returns:
        ContextSnapshot pronto para injetar no prompt
    """
    snapshot = ContextSnapshot(
        active_files=list(active_files or []),
        workspace_files=_get_workspace_files(),
        console_errors=list(console_errors or []),
        last_stdout=last_stdout or "",
        last_stderr=last_stderr or "",
        sandbox_path=str(SANDBOX_DIR),
    )

    # Workspace state
    n = len(snapshot.workspace_files)
    snapshot.workspace_state = f"{n} itens no workspace (raiz)" if n else "Workspace vazio"

    # Chat summary (resumo curto se disponível)
    if user_id and chat_id:
        try:
            from core.memory import get_messages
            msgs = get_messages(chat_id, user_id) or []
            if msgs:
                recent = msgs[-4:]
                parts = [f"[{m.get('role','?')}]: {(m.get('content') or '')[:100]}..." for m in recent]
                snapshot.chat_summary = "\n".join(parts)
        except Exception:
            pass

    if extra:
        for k, v in extra.items():
            if hasattr(snapshot, k):
                setattr(snapshot, k, v)

    return snapshot


def snapshot_to_prompt(snapshot: ContextSnapshot, max_chars: int = 1500) -> str:
    """Converte snapshot em texto para injetar no prompt da IA."""
    lines: List[str] = []

    if snapshot.active_files:
        lines.append("[ARQUIVOS ATIVOS]")
        for f in snapshot.active_files[:5]:
            lines.append(f"  - {f}")
        lines.append("")

    if snapshot.console_errors:
        lines.append("[ERROS DO CONSOLE]")
        for e in snapshot.console_errors[:5]:
            lines.append(f"  - {e[:200]}")
        lines.append("")

    if snapshot.last_stderr:
        lines.append("[ÚLTIMA EXECUÇÃO — stderr]")
        lines.append(snapshot.last_stderr[:500])
        lines.append("")

    if snapshot.workspace_state:
        lines.append(f"[WORKSPACE] {snapshot.workspace_state}")

    out = "\n".join(lines).strip()
    return out[:max_chars] if len(out) > max_chars else out
