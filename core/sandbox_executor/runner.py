"""
Sandbox Runner — Executa código em subprocess isolado.

- Timeout configurável
- Limite de RAM (Unix: resource.setrlimit; Windows: só timeout)
- Captura stdout/stderr
- Não roda no worker principal (evita SIGKILL)
"""

import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

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


def _preexec_limit_memory():
    """Limita RAM do processo-filho (apenas Unix)."""
    try:
        import resource
        # 256 MB
        limit = 256 * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    except (ImportError, OSError, ValueError):
        pass


def run_code(
    code: str,
    lang: str = "python",
    cwd: Optional[Path] = None,
    timeout: int = 30,
    max_ram_mb: int = 256,
) -> RunResult:
    """
    Executa código em subprocess isolado.

    Args:
        code: código fonte
        lang: python | javascript | node
        cwd: diretório de trabalho (default: sandbox)
        timeout: segundos máximos
        max_ram_mb: limite de RAM em MB (só Unix)

    Returns:
        RunResult com stdout, stderr, exit_code
    """
    if not code or not code.strip():
        return RunResult(ok=False, stderr="Código vazio", exit_code=-1)

    work_dir = Path(cwd) if cwd else Path(SANDBOX_DIR)
    work_dir.mkdir(parents=True, exist_ok=True)
    work_dir = work_dir.resolve()

    if timeout > 60:
        timeout = 60
    if timeout < 1:
        timeout = 15

    script_name = "_run_script.py" if lang in ("python", "py") else "_run_script.js"
    script_path = work_dir / script_name

    try:
        script_path.write_text(code, encoding="utf-8", errors="replace")
    except Exception as e:
        return RunResult(ok=False, stderr=str(e), exit_code=-1)

    cmd: Optional[list] = None
    if lang in ("python", "py"):
        cmd = [sys.executable, str(script_path)]
    elif lang in ("javascript", "js", "node"):
        cmd = ["node", str(script_path)]

    if not cmd:
        return RunResult(ok=False, stderr=f"Linguagem '{lang}' não suportada", exit_code=-1)

    preexec_fn = None
    if sys.platform != "win32":
        preexec_fn = _preexec_limit_memory

    try:
        result = subprocess.run(
            cmd,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
            preexec_fn=preexec_fn,
        )
        return RunResult(
            ok=result.returncode == 0,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
            exit_code=result.returncode,
            timed_out=False,
        )
    except subprocess.TimeoutExpired:
        return RunResult(
            ok=False,
            stdout="",
            stderr="Timeout na execução",
            exit_code=-1,
            timed_out=True,
            feedback=f"Timeout ({timeout}s). Considere simplificar o código.",
        )
    except FileNotFoundError:
        interp = "Python" if lang in ("python", "py") else "Node"
        return RunResult(
            ok=False,
            stdout="",
            stderr=f"{interp} não encontrado no servidor",
            exit_code=-1,
        )
    except Exception as e:
        return RunResult(ok=False, stdout="", stderr=str(e), exit_code=-1)
