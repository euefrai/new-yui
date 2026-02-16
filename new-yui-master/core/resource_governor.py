# ==========================================================
# YUI RESOURCE GOVERNOR
# Controle inteligente de recursos — decide "posso executar isso agora?"
#
# Observa RAM, CPU, estado do sistema.
# Liga/desliga features automaticamente.
# ==========================================================

from dataclasses import dataclass
from typing import Optional, Tuple

# Thresholds (configuráveis via env no futuro)
RAM_PREVIEW_MAX = 75.0      # % — preview só se RAM < 75%
RAM_HEAVY_AGENT_MAX = 80.0  # % — agent pesado só se RAM < 80%
CPU_HEAVY_AGENT_MAX = 85.0  # % — agent pesado só se CPU < 85%
CPU_PLANNER_MAX = 90.0      # % — planner só se CPU < 90%
RAM_WATCHERS_MAX = 70.0     # % — watchers ativos só se RAM < 70%


@dataclass
class GovernorDecision:
    """Decisão do Governor: allow + motivo."""
    allow: bool
    reason: str


def _get_telemetry() -> Tuple[float, float]:
    """Retorna (ram_percent, cpu_percent). Usa cache do self_monitoring."""
    try:
        from core.self_monitoring import get_system_snapshot
        snap = get_system_snapshot(use_cache=True)
        if snap:
            return (snap.ram_percent, snap.cpu_percent)
    except Exception:
        pass
    return (0.0, 0.0)


def allow_preview(ram_usage: Optional[float] = None) -> GovernorDecision:
    """
    Preview (live HTML) só quando RAM permitir.
    """
    ram = ram_usage if ram_usage is not None else _get_telemetry()[0]
    if ram >= RAM_PREVIEW_MAX:
        d = GovernorDecision(False, f"RAM {ram:.0f}% >= {RAM_PREVIEW_MAX}%")
    else:
        d = GovernorDecision(True, f"RAM {ram:.0f}% ok")
    _record_governor("preview", d)
    return d


def allow_heavy_agent(cpu_usage: Optional[float] = None, ram_usage: Optional[float] = None) -> GovernorDecision:
    """
    Agent pesado (planner, tools múltiplas) só quando CPU e RAM permitirem.
    """
    ram_t, cpu_t = _get_telemetry()
    ram = ram_usage if ram_usage is not None else ram_t
    cpu = cpu_usage if cpu_usage is not None else cpu_t
    if cpu >= CPU_HEAVY_AGENT_MAX:
        d = GovernorDecision(False, f"CPU {cpu:.0f}% >= {CPU_HEAVY_AGENT_MAX}%")
    elif ram >= RAM_HEAVY_AGENT_MAX:
        d = GovernorDecision(False, f"RAM {ram:.0f}% >= {RAM_HEAVY_AGENT_MAX}%")
    else:
        d = GovernorDecision(True, f"CPU {cpu:.0f}%, RAM {ram:.0f}% ok")
    _record_governor("heavy_agent", d)
    return d


def allow_planner(cpu_usage: Optional[float] = None) -> GovernorDecision:
    """
    Planner só quando CPU permitir.
    """
    cpu = cpu_usage if cpu_usage is not None else _get_telemetry()[1]
    if cpu >= CPU_PLANNER_MAX:
        d = GovernorDecision(False, f"CPU {cpu:.0f}% >= {CPU_PLANNER_MAX}%")
    else:
        d = GovernorDecision(True, f"CPU {cpu:.0f}% ok")
    _record_governor("planner", d)
    return d


def allow_watchers(ram_usage: Optional[float] = None) -> GovernorDecision:
    """
    File watchers só quando RAM permitir.
    """
    ram = ram_usage if ram_usage is not None else _get_telemetry()[0]
    if ram >= RAM_WATCHERS_MAX:
        d = GovernorDecision(False, f"RAM {ram:.0f}% >= {RAM_WATCHERS_MAX}%")
    else:
        d = GovernorDecision(True, f"RAM {ram:.0f}% ok")
    _record_governor("watchers", d)
    return d


def allow_execution_graph(ram_usage: Optional[float] = None, cpu_usage: Optional[float] = None) -> GovernorDecision:
    """
    Execution Graph só quando recursos permitirem.
    """
    return allow_heavy_agent(cpu_usage=cpu_usage, ram_usage=ram_usage)


def _record_governor(feature: str, d: GovernorDecision) -> None:
    """Registra decisão no Observability (apenas quando bloqueia)."""
    if not d.allow:
        try:
            from core.observability import record_activity
            record_activity("governor", f"Governor: {feature}", d.reason)
        except Exception:
            pass


# ==========================================================
# Governor singleton (para consultas rápidas)
# ==========================================================

class ResourceGovernor:
    """
    Cérebro que decide: posso executar isso agora ou não?

    Uso:
        if governor.allow_preview():
            start_live_preview()
    """

    def allow_preview(self, ram: Optional[float] = None) -> GovernorDecision:
        return allow_preview(ram)

    def allow_heavy_agent(self, cpu: Optional[float] = None, ram: Optional[float] = None) -> GovernorDecision:
        return allow_heavy_agent(cpu_usage=cpu, ram_usage=ram)

    def allow_planner(self, cpu: Optional[float] = None) -> GovernorDecision:
        return allow_planner(cpu_usage=cpu)

    def allow_watchers(self, ram: Optional[float] = None) -> GovernorDecision:
        return allow_watchers(ram_usage=ram)

    def allow_execution_graph(self, ram: Optional[float] = None, cpu: Optional[float] = None) -> GovernorDecision:
        return allow_execution_graph(ram_usage=ram, cpu_usage=cpu)


_governor: Optional[ResourceGovernor] = None


def get_governor() -> ResourceGovernor:
    """Retorna o Resource Governor singleton."""
    global _governor
    if _governor is None:
        _governor = ResourceGovernor()
    return _governor
