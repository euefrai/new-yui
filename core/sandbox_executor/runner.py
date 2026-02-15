"""
Sandbox Runner — Executa código em subprocess isolado.
- Timeout configurável
- Limite de RAM (Unix: resource.setrlimit)
- Captura stdout/stderr
- Sistema de métricas para observabilidade
"""

import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Optional, Dict, Any

try:
    from config.settings import SANDBOX_DIR
except Exception:
    SANDBOX_DIR = Path(__file__).resolve().parents[2] / "sandbox"


@dataclass
class RunResult:
    """Resultado da execução isolada."""
    ok: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    timed_out: bool = False
    feedback: str = ""


# --- Sistema de Métricas ---
_metrics_lock = Lock()
_metrics: Dict[str, Any] = {
    "executions_total": 0,
    "success_total": 0,
    "failed_total": 0,
    "timed_out_total": 0,
    "by_lang": {},
}


def _bump_metric(lang: str, ok: bool, timed_out: bool = False) -> None:
    """Atualiza as métricas de execução de forma thread-safe."""
    lang_key = (lang or "unknown").lower()
    with _metrics_lock:
        _metrics["executions_total"] += 1
        if ok:
            _metrics["success_total"] += 1
        else:
            _metrics["failed_total"] += 1
        if timed_out:
            _metrics["timed_out_total"] += 1

        by_lang = _metrics.setdefault("by_lang", {})
        current = by_lang.get(lang_key, {"executions": 0, "success": 0, "failed": 0, "timed_out": 0})
        current["executions"] += 1
        if ok:
            current["success"] += 1
        else:
            current["failed"] += 1
        if timed_out:
            current["timed_out"] += 1
        by_lang[lang_key] = current


def get_execution_metrics() -> Dict[str, Any]:
    """Retorna estatísticas de uso do Sandbox para observabilidade."""
    with _metrics_lock:
        return {
            "executions_total": _metrics.get("executions_total", 0),
            "success_total": _metrics.get("success_total", 0),
            "failed_total": _metrics.get("failed_total", 0),
            "timed_out_total": _metrics.get("timed_out_total", 0),
            "by_lang": dict(_metrics.get("by_lang", {})),
        }


def _preexec_limit_memory(max_ram_mb: int = 256) -> None:
    """Limita RAM do processo-filho (apenas Unix/Linux)."""
    try:
        import resource
        ram_mb = max(128, int(max_ram_mb or 256))
        limit = ram_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    except (ImportError, OSError, ValueError, TypeError):
        pass


def run_code(
    code: str,
    lang: str = "python",
    cwd: Optional[Path] = None,
    timeout: int = 30,
    max_ram_mb: int = 256,
) -> RunResult:
    """Executa código em subprocess isolado com limites de recurso."""
    if not code or not code.strip():
        _bump_metric(lang, ok=False)
        return RunResult(ok=False, stderr="Código vazio", exit_code=-1)

    work_dir = Path(cwd) if cwd else Path(SANDBOX_DIR)
    work_dir.mkdir(parents=True, exist_ok=True)
    work_dir = work_dir.resolve()

    timeout = max(1, min(timeout, 60))

    script_name = "_run_script.py" if lang in ("python", "py") else "_run_script.js"
    script_path = work_dir / script_name

    try:
        script_path.write_text(code, encoding="utf-8", errors="replace")
    except Exception as e:
        _bump_metric(lang, ok=False)
        return RunResult(ok=False, stderr=str(e), exit_code=-1)

    cmd = None
    if lang in ("python", "py"):
        cmd = [sys.executable, str(script_path)]
    elif lang in ("javascript", "js", "node"):
        cmd = ["node", str(script_path)]

    if not cmd:
        _bump_metric(lang, ok=False)
        return RunResult(ok=False, stderr=f"Linguagem '{lang}' não suportada", exit_code=-1)

    preexec_fn = None
    if sys.platform != "win32" and lang in ("python", "py"):
        preexec_fn = lambda: _preexec_limit_memory(max_ram_mb)

    try:
        result = subprocess.run(
            cmd,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
            preexec_fn=preexec_fn,
        )

        run_result = RunResult(
            ok=result.returncode == 0,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
            exit_code=result.returncode,
            timed_out=False,
        )
        _bump_metric(lang, ok=run_result.ok)
        return run_result

    except subprocess.TimeoutExpired:
        _bump_metric(lang, ok=False, timed_out=True)
        return RunResult(
            ok=False,
            stderr=f"Timeout na execução ({timeout}s).",
            exit_code=-1,
            timed_out=True,
            feedback="O código demorou demais para responder. Verifique loops infinitos.",
        )
    except FileNotFoundError:
        _bump_metric(lang, ok=False)
        interp = "Python" if lang in ("python", "py") else "Node"
        return RunResult(
            ok=False,
            stdout="",
            stderr=f"{interp} não encontrado no servidor",
            exit_code=-1,
        )
    except Exception as e:
        _bump_metric(lang, ok=False)
        return RunResult(ok=False, stdout="", stderr=str(e), exit_code=-1)
