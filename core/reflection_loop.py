# ==========================================================
# YUI REFLECTION LOOP — Autoavaliação interna
#
# Planeja → Executa → Avalia → Ajusta
#
# Não é IA extra. É telemetria inteligente que adapta o comportamento.
# A Yui passa a evoluir enquanto roda: aprende padrões de RAM,
# evita tarefas pesadas sozinha, reduz SIGKILL antes de acontecer.
#
# Estados: "ok" | "modo_economia" | "dividir_tasks"
# ==========================================================

import os
from typing import Any, Dict, Optional


# Limites configuráveis (telemetria leve)
DEFAULT_RAM_THRESHOLD_MB = 1200
DEFAULT_TIME_THRESHOLD_SEC = 3.0


class ReflectionLoop:
    """
    Avalia contexto pós-execução e retorna estado para o Planner ajustar.
    Telemetria leve: RAM, tempo, sucesso.
    """

    def __init__(
        self,
        ram_threshold_mb: Optional[float] = None,
        time_threshold_sec: Optional[float] = None,
    ):
        self.ram_threshold = ram_threshold_mb or float(
            os.environ.get("YUI_REFLECTION_RAM_MB", str(DEFAULT_RAM_THRESHOLD_MB))
        )
        self.time_threshold = time_threshold_sec or float(
            os.environ.get("YUI_REFLECTION_TEMPO_SEC", str(DEFAULT_TIME_THRESHOLD_SEC))
        )

    def avaliar(self, contexto: Dict[str, Any]) -> str:
        """
        Avalia dados da execução e retorna estado de reflexão.
        "ok" | "modo_economia" | "dividir_tasks"
        """
        if not contexto:
            return "ok"

        memoria = contexto.get("memoria") or contexto.get("memoria_usada") or 0
        tempo = contexto.get("tempo") or contexto.get("tempo_execucao") or 0
        sucesso = contexto.get("sucesso", True)

        # Prioridade: RAM alta → modo economia (gerar menos código por vez)
        if memoria > self.ram_threshold:
            return "modo_economia"

        # Tarefas muito lentas → sugerir dividir em etapas menores
        if tempo > self.time_threshold:
            return "dividir_tasks"

        return "ok"


# --- Singleton + estado global ---
_loop: Optional[ReflectionLoop] = None
_estado_reflexao: str = "ok"


def get_reflection_loop() -> ReflectionLoop:
    """Retorna o ReflectionLoop singleton."""
    global _loop
    if _loop is None:
        _loop = ReflectionLoop()
    return _loop


def avaliar_e_armazenar(contexto: Dict[str, Any]) -> str:
    """
    Avalia contexto, armazena resultado e retorna.
    Chamado após task_done/task_failed.
    Emite memoria_alta quando modo_economia.
    """
    global _estado_reflexao
    loop = get_reflection_loop()
    _estado_reflexao = loop.avaliar(contexto)
    if _estado_reflexao == "modo_economia":
        try:
            from core.event_bus import emit
            ram = contexto.get("memoria_usada") or contexto.get("memoria") or 0
            emit("memoria_alta", ram_mb=ram, threshold=loop.ram_threshold)
        except Exception:
            pass
    return _estado_reflexao


def get_estado_reflexao() -> str:
    """Retorna último estado de reflexão (para Planner usar)."""
    return _estado_reflexao


def set_estado_reflexao(estado: str) -> None:
    """Define estado manualmente (fallback)."""
    global _estado_reflexao
    _estado_reflexao = estado or "ok"
