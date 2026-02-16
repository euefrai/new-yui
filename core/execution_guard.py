# ==========================================================
# YUI EXECUTION GUARD — Resource Manager
#
# Vigia CPU, RAM e duração das tarefas antes do Zeabur matar tudo com SIGKILL.
#
# Fluxo: Planner → Execution Guard → Task Engine
#
# A Yui decide: "essa tarefa vai estourar memória… melhor esperar"
# ==========================================================

import time
from dataclasses import dataclass, field
from typing import Optional, Tuple

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None


@dataclass
class GuardDecision:
    """Decisão do guard: ok + motivo."""
    ok: bool
    reason: str
    ram_used_mb: float = 0.0
    ram_limit_mb: float = 0.0
    cpu_percent: float = 0.0
    cpu_limit: float = 0.0


class ExecutionGuard:
    """
    Vigia recursos antes de executar tarefas.
    Evita SIGKILL: pausa quando CPU/RAM estão altos.
    """

    def __init__(
        self,
        ram_limit_mb: float = 1500.0,
        cpu_limit_percent: float = 85.0,
        ram_limit_percent: Optional[float] = None,
        wait_interval_sec: float = 1.0,
        max_wait_sec: float = 30.0,
    ):
        """
        ram_limit_mb: RAM usada em MB (ex: 1500 = 1.5GB). Se None, usa ram_limit_percent.
        cpu_limit_percent: CPU máxima permitida (ex: 85).
        ram_limit_percent: alternativo — RAM em % (ex: 85). Se definido, sobrepõe ram_limit_mb.
        wait_interval_sec: quanto esperar entre checagens.
        max_wait_sec: tempo máximo esperando antes de executar mesmo assim.
        """
        self.ram_limit_mb = ram_limit_mb
        self.cpu_limit = cpu_limit_percent
        self.ram_limit_percent = ram_limit_percent
        self.wait_interval = wait_interval_sec
        self.max_wait = max_wait_sec

    def _telemetry(self) -> Tuple[float, float, float]:
        """Retorna (ram_used_mb, ram_percent, cpu_percent)."""
        if not PSUTIL_AVAILABLE or psutil is None:
            return (0.0, 0.0, 0.0)
        try:
            mem = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=None)
            ram_mb = mem.used / (1024 * 1024)
            ram_pct = mem.percent
            return (ram_mb, ram_pct, cpu)
        except Exception:
            return (0.0, 0.0, 0.0)

    def memoria_ok(self, limite_mb: Optional[float] = None) -> GuardDecision:
        """
        RAM ok? Se ram_limit_percent definido, usa %; senão usa MB.
        """
        ram_mb, ram_pct, _ = self._telemetry()
        limit_mb = limite_mb if limite_mb is not None else self.ram_limit_mb

        if self.ram_limit_percent is not None:
            ok = ram_pct < self.ram_limit_percent
            reason = f"RAM {ram_pct:.0f}% {'<' if ok else '>='} {self.ram_limit_percent}%"
            return GuardDecision(
                ok=ok,
                reason=reason,
                ram_used_mb=ram_mb,
                ram_limit_mb=0,
                cpu_percent=0,
                cpu_limit=0,
            )
        ok = ram_mb < limit_mb
        reason = f"RAM {ram_mb:.0f}MB {'<' if ok else '>='} {limit_mb:.0f}MB"
        return GuardDecision(
            ok=ok,
            reason=reason,
            ram_used_mb=ram_mb,
            ram_limit_mb=limit_mb,
        )

    def cpu_ok(self, limite: Optional[float] = None) -> GuardDecision:
        """CPU ok?"""
        _, ram_pct, cpu = self._telemetry()
        limit = limite if limite is not None else self.cpu_limit
        ok = cpu < limit
        reason = f"CPU {cpu:.0f}% {'<' if ok else '>='} {limit}%"
        return GuardDecision(
            ok=ok,
            reason=reason,
            cpu_percent=cpu,
            cpu_limit=limit,
            ram_used_mb=0,
            ram_limit_mb=0,
        )

    def pode_executar(self) -> GuardDecision:
        """Combinação: RAM e CPU ok."""
        ram_mb, ram_pct, cpu = self._telemetry()

        if self.ram_limit_percent is not None:
            ram_ok = ram_pct < self.ram_limit_percent
        else:
            ram_ok = ram_mb < self.ram_limit_mb

        cpu_ok = cpu < self.cpu_limit

        if ram_ok and cpu_ok:
            return GuardDecision(
                ok=True,
                reason=f"RAM {ram_pct:.0f}%, CPU {cpu:.0f}% ok",
                ram_used_mb=ram_mb,
                ram_limit_mb=self.ram_limit_mb,
                cpu_percent=cpu,
                cpu_limit=self.cpu_limit,
            )

        parts = []
        if not ram_ok:
            parts.append(f"RAM {ram_pct:.0f}% alto" if self.ram_limit_percent else f"RAM {ram_mb:.0f}MB alto")
        if not cpu_ok:
            parts.append(f"CPU {cpu:.0f}% alto")
        return GuardDecision(
            ok=False,
            reason="; ".join(parts),
            ram_used_mb=ram_mb,
            ram_limit_mb=self.ram_limit_mb,
            cpu_percent=cpu,
            cpu_limit=self.cpu_limit,
        )

    def wait_if_needed(self) -> GuardDecision:
        """
        Espera até pode_executar() ou max_wait_sec.
        Retorna a decisão final (pode ter dado timeout e executar mesmo assim).
        """
        start = time.monotonic()
        while True:
            d = self.pode_executar()
            if d.ok:
                return d
            try:
                from core.observability import record_activity
                record_activity("guard", "Execution Guard aguardando", d.reason)
            except Exception:
                pass
            elapsed = time.monotonic() - start
            if elapsed >= self.max_wait:
                return GuardDecision(
                    ok=True,
                    reason=f"Timeout {self.max_wait:.0f}s — executando mesmo assim",
                    ram_used_mb=d.ram_used_mb,
                    ram_limit_mb=d.ram_limit_mb,
                    cpu_percent=d.cpu_percent,
                    cpu_limit=d.cpu_limit,
                )
            time.sleep(self.wait_interval)


# --- Singleton ---
_guard: Optional[ExecutionGuard] = None


def get_guard() -> ExecutionGuard:
    """Retorna o Execution Guard singleton."""
    global _guard
    if _guard is None:
        import os
        ram_mb = float(os.environ.get("YUI_GUARD_RAM_MB", "1500"))
        cpu_pct = float(os.environ.get("YUI_GUARD_CPU_PCT", "85"))
        ram_pct = os.environ.get("YUI_GUARD_RAM_PCT")
        ram_pct = float(ram_pct) if ram_pct else None
        _guard = ExecutionGuard(
            ram_limit_mb=ram_mb,
            cpu_limit_percent=cpu_pct,
            ram_limit_percent=ram_pct,
        )
    return _guard
