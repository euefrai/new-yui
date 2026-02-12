"""
Arbitration Engine — Decision Layer (Arbiter).

Decide qual persona lidera a ação: Yui (suporte, UX, visão ampla) ou
Heathcliff (engenharia pesada) — ou se as duas devem colaborar (hybrid).

Evita inconsistência de estilo e retrabalho. É o "Tech Lead invisível".
"""

from dataclasses import dataclass
from typing import Optional

# Heurísticas: palavras que indicam dominância de cada persona
_HEATHCLIFF_SIGNALS = [
    "refatorar", "refatoração", "backend", "arquitetura", "api", "endpoint",
    "banco de dados", "sql", "migração", "deploy", "docker", "ci/cd",
    "otimizar", "performance", "escalar", "microserviço", "teste unitário",
    "corrigir bug", "debug", "erro", "exception", "stack trace",
    "criar projeto", "implementar", "codificar", "escrever código",
]
_YUI_SIGNALS = [
    "ui", "interface", "ux", "design", "texto", "fluxo", "experiência",
    "explicar", "como funciona", "o que é", "ajuda", "dúvida",
    "traduzir", "formatação", "mensagem", "feedback", "resposta",
]
# Sinais que sugerem colaboração (engenharia + UX)
_HYBRID_SIGNALS = [
    "fullstack", "app completo", "desde o zero", "do zero",
]


@dataclass
class ArbitrationResult:
    """Resultado da arbitragem: qual persona lidera e por quê."""
    leader: str  # "yui" | "heathcliff" | "hybrid"
    confidence: float
    reason: str


def _score_signals(text: str, signals: list[str]) -> float:
    """Score 0-1 baseado em matches nos sinais."""
    if not text or not signals:
        return 0.0
    lower = text.lower().strip()
    matches = sum(1 for s in signals if s.lower() in lower)
    return min(1.0, matches * 0.35) if matches else 0.0


def decide_leader(
    user_message: str,
    user_preference: Optional[str] = None,
    active_files: Optional[list] = None,
    has_console_errors: bool = False,
) -> ArbitrationResult:
    """
    Decide qual persona deve liderar a resposta.

    Args:
        user_message: mensagem do usuário
        user_preference: preferência explícita ("yui" | "heathcliff" | None).
            Se None, usa apenas heurísticas. Se informada, pode influenciar
            em empate.

    Returns:
        ArbitrationResult com leader, confidence e reason.
    """
    msg = (user_message or "").strip()
    active_files = active_files or []

    # Boost Heathcliff quando há erros no console (correção de código)
    if has_console_errors and any(w in (msg or "").lower() for w in ("erro", "error", "corrigir", "fix", "consertar")):
        return ArbitrationResult(
            leader="heathcliff",
            confidence=0.85,
            reason="Erros no console + pedido de correção → Heathcliff.",
        )

    if not msg:
        return ArbitrationResult(
            leader="yui",
            confidence=0.5,
            reason="Mensagem vazia; padrão Yui.",
        )

    h_score = _score_signals(msg, _HEATHCLIFF_SIGNALS)
    y_score = _score_signals(msg, _YUI_SIGNALS)
    hy_score = _score_signals(msg, _HYBRID_SIGNALS)

    # Hybrid boost: se houver sinais de fullstack, favorece colaboração
    if hy_score > 0.3:
        return ArbitrationResult(
            leader="hybrid",
            confidence=min(0.9, 0.5 + hy_score),
            reason=f"Sinais de fullstack/collab (score={hy_score:.2f}).",
        )

    if h_score > y_score and h_score > 0.2:
        return ArbitrationResult(
            leader="heathcliff",
            confidence=min(0.95, 0.4 + h_score),
            reason=f"Engenharia predominante (h={h_score:.2f}, y={y_score:.2f}).",
        )

    if y_score > h_score and y_score > 0.2:
        return ArbitrationResult(
            leader="yui",
            confidence=min(0.95, 0.4 + y_score),
            reason=f"UX/suporte predominante (y={y_score:.2f}, h={h_score:.2f}).",
        )

    # Empate ou sem sinais claros: usa preferência do usuário ou default
    if user_preference in ("heathcliff", "yui"):
        return ArbitrationResult(
            leader=user_preference,
            confidence=0.6,
            reason=f"Sem sinais claros; usando preferência do usuário ({user_preference}).",
        )

    # Default: Yui (mais amigável para perguntas ambíguas)
    return ArbitrationResult(
        leader="yui",
        confidence=0.5,
        reason=f"Sinais ambíguos (h={h_score:.2f}, y={y_score:.2f}); padrão Yui.",
    )


def get_hybrid_modifier() -> str:
    """Texto para injetar no prompt quando leader=hybrid (Heathcliff + UX)."""
    return (
        "Modo colaborativo: você é o Heathcliff (engenharia pesada), mas "
        "deve considerar também a perspectiva da Yui (UX, fluxo do usuário, clareza). "
        "Combine solidez técnica com experiência de uso."
    )
