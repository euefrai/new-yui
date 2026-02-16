# ==========================================================
# YUI SELF-MONITORING (Infrastructure Awareness)
# Lê CPU, RAM do servidor → alimenta Cognitive Budget.
# "Sensores" da Yui: ela passa a saber como está o ambiente.
# ==========================================================

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

# Thresholds para modo FAST (economia)
CPU_HIGH_THRESHOLD = 85.0   # % → entra em modo econômico
RAM_HIGH_THRESHOLD = 85.0   # % → entra em modo econômico
CPU_CRITICAL = 95.0
RAM_CRITICAL = 95.0

# Cache para reduzir CPU: 20s em produção (Zeabur, Tencent, VPS)
_CACHE_SEC = 20.0
_last_snapshot: Optional[Dict[str, Any]] = None
_last_snapshot_time: float = 0


@dataclass
class SystemSnapshot:
    """Snapshot de saúde do servidor."""
    cpu_percent: float
    ram_percent: float
    ram_used_mb: float
    ram_total_mb: float
    mode: str  # "normal" | "fast" | "critical"
    message: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_percent": round(self.cpu_percent, 1),
            "ram_percent": round(self.ram_percent, 1),
            "ram_used_mb": round(self.ram_used_mb, 1),
            "ram_total_mb": round(self.ram_total_mb, 1),
            "mode": self.mode,
            "message": self.message,
            "timestamp": self.timestamp,
        }


def get_system_snapshot(use_cache: bool = True) -> Optional[SystemSnapshot]:
    """
    Lê CPU e RAM do servidor.
    Retorna None se psutil não estiver instalado.
    """
    global _last_snapshot, _last_snapshot_time
    if not PSUTIL_AVAILABLE or psutil is None:
        return None

    now = time.monotonic()
    if use_cache and _last_snapshot and (now - _last_snapshot_time) < _CACHE_SEC:
        return _last_snapshot

    try:
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        ram_pct = mem.percent
        ram_used = mem.used / (1024 * 1024)
        ram_total = mem.total / (1024 * 1024)

        if cpu >= CPU_CRITICAL or ram_pct >= RAM_CRITICAL:
            mode = "critical"
            message = "Carga crítica no servidor. Operando em modo mínimo."
        elif cpu >= CPU_HIGH_THRESHOLD or ram_pct >= RAM_HIGH_THRESHOLD:
            mode = "fast"
            message = "Estou operando em modo de economia de energia devido à carga do servidor."
        else:
            mode = "normal"
            message = ""

        snap = SystemSnapshot(
            cpu_percent=cpu,
            ram_percent=ram_pct,
            ram_used_mb=ram_used,
            ram_total_mb=ram_total,
            mode=mode,
            message=message,
        )
        _last_snapshot = snap
        _last_snapshot_time = now
        return snap
    except Exception:
        return None


def should_use_fast_mode() -> bool:
    """True se CPU ou RAM estão altos → Cognitive Budget deve usar modo econômico."""
    snap = get_system_snapshot()
    if not snap:
        return False
    return snap.mode in ("fast", "critical")


def get_system_state_for_prompt(always_include: bool = False) -> str:
    """
    Texto para injetar no prompt do sistema.
    always_include=True (Heathcliff): sempre inclui RAM/CPU para sugerir código mais leve.
    always_include=False: só inclui quando sobrecarregado.
    """
    snap = get_system_snapshot()
    if not snap:
        return ""
    cpu = getattr(snap, "cpu_percent", 0) or 0
    ram = getattr(snap, "ram_percent", 0) or 0
    mode = getattr(snap, "mode", "normal") or "normal"
    if always_include:
        base = f"[Telemetria] Sistema: CPU {cpu:.0f}%, RAM {ram:.0f}%."
        if mode in ("fast", "critical"):
            base += (
                " Servidor sobrecarregado. Sugira código OTIMIZADO e LEVE por padrão: "
                "evite soluções pesadas, prefira algoritmos eficientes, menos dependências."
            )
        return base
    if mode == "normal":
        return ""
    return (
        f"[Autopercepção] O servidor está com carga elevada "
        f"(CPU: {cpu:.0f}%, RAM: {ram:.0f}%). "
        "Se o usuário perguntar sobre performance ou lentidão, informe de forma proativa "
        "que você está operando em modo de economia de energia e que as respostas podem ser "
        "mais resumidas até a carga normalizar."
    )
