# ==========================================================
# YUI COGNITIVE BUDGET SYSTEM
# Orçamento completo: tokens, tempo, memória, profundidade.
# "Isso merece gastar pensamento profundo ou não?"
# ==========================================================

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

# Estimativa: ~4 chars = 1 token (pt/en)
CHARS_PER_TOKEN = 4

# Budgets padrão (por turno)
DEFAULT_TOKEN_BUDGET = 8000
DEFAULT_TIME_BUDGET_SEC = 60
DEFAULT_MEMORY_BUDGET = 12
DEFAULT_DEPTH_LEVELS = ("minimal", "shallow", "normal", "deep")


@dataclass
class CognitiveBudget:
    """
    Orçamento cognitivo por turno.
    tokens: orçamento de tokens (estimado)
    time_sec: tempo máximo em segundos
    memory: max itens de contexto
    depth: profundidade de raciocínio (0-3)
    """

    token_budget: int = DEFAULT_TOKEN_BUDGET
    time_budget_sec: float = DEFAULT_TIME_BUDGET_SEC
    memory_budget: int = DEFAULT_MEMORY_BUDGET

    token_used: int = 0
    start_time: float = field(default_factory=time.monotonic)

    def estimate_tokens(self, text: str) -> int:
        """Estima tokens a partir do texto."""
        if not text:
            return 0
        return max(1, len(text) // CHARS_PER_TOKEN)

    def consume_tokens(self, count: int) -> None:
        """Registra consumo de tokens."""
        self.token_used += count

    def can_afford_tokens(self, count: int) -> bool:
        """Verifica se ainda há orçamento de tokens."""
        return (self.token_used + count) <= self.token_budget

    def can_afford_time(self) -> bool:
        """Verifica se ainda há orçamento de tempo."""
        elapsed = time.monotonic() - self.start_time
        return elapsed < self.time_budget_sec

    def can_afford_memory(self, context_size: int) -> bool:
        """Verifica se contexto cabe no orçamento de memória."""
        return context_size <= self.memory_budget

    def can_afford_reflection(self) -> bool:
        """Reflexão consome tokens e tempo — vale a pena?"""
        return self.can_afford_tokens(500) and self.can_afford_time()

    def recommend_depth(
        self,
        user_message: str = "",
        energy: Optional[float] = None,
        context_size: int = 0,
        meta_signals: Optional[Dict[str, Any]] = None,
        server_load_high: bool = False,
    ) -> str:
        """
        "Isso merece pensamento profundo ou não?"
        Retorna: minimal | shallow | normal | deep
        server_load_high: quando CPU/RAM altos → modo FAST (economia).
        """
        meta = meta_signals or {}

        if meta.get("simplified_mode"):
            return "minimal"
        if server_load_high:
            return "minimal"
        if energy is not None and energy < 10:
            return "minimal"
        if energy is not None and energy < 20:
            return "shallow"
        if not self.can_afford_time():
            return "minimal"
        if not self.can_afford_tokens(3000):
            return "shallow"
        if not self.can_afford_memory(context_size):
            return "shallow"

        msg = (user_message or "").lower()
        complexity = 0
        if any(x in msg for x in ("analise", "analis", "explique", "crie", "criar", "projeto", "arquitetura")):
            complexity = 2
        elif any(x in msg for x in ("corrigir", "bug", "erro", "problema")):
            complexity = 2
        elif len(msg) > 100:
            complexity = 1

        if complexity >= 2 and self.can_afford_tokens(5000):
            return "deep"
        if complexity >= 1:
            return "normal"
        return "shallow"

    def get_max_context_items(self, depth: str) -> int:
        """Retorna max itens de contexto por profundidade."""
        return {"minimal": 3, "shallow": 5, "normal": 8, "deep": 12}.get(depth, 5)

    def get_allow_reflection(self, depth: str) -> bool:
        """Reflexão só em normal/deep."""
        return depth in ("normal", "deep")

    def get_max_plan_steps(self, depth: str) -> int:
        """Retorna max steps do plano por profundidade."""
        return {"minimal": 1, "shallow": 2, "normal": 4, "deep": 6}.get(depth, 3)


_budget: Optional[CognitiveBudget] = None


def get_cognitive_budget() -> CognitiveBudget:
    """Retorna instância do budget (resetada a cada turno pelo caller)."""
    global _budget
    if _budget is None:
        _budget = CognitiveBudget()
    return _budget


def reset_budget_for_turn() -> CognitiveBudget:
    """Reseta budget para novo turno."""
    global _budget
    _budget = CognitiveBudget()
    return _budget
