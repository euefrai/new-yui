"""
Sandbox Executor — Execução isolada de código.

Anti-SIGKILL: subprocess isolado, timeout, limite de RAM (Unix).
"""

from core.sandbox_executor.runner import run_code, RunResult

__all__ = ["run_code", "RunResult"]
