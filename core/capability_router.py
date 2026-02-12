# ==========================================================
# YUI CAPABILITY ROUTER
# Roteador de habilidades — decide qual módulo deve resolver.
#
# Antes do planner: Intent → Capability Router → melhor módulo
# Evita que tarefas simples cheguem ao agente pesado.
# ==========================================================

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Sinais por tipo de capability
_CODE_SIGNALS = [
    "criar", "cria", "gerar", "fazer", "implementar", "codificar", "escrever",
    "refatorar", "refatoração", "backend", "api", "endpoint", "código", "codigo",
    "calculadora", "login", "sistema", "projeto", "site", "arquivo",
]
_MEMORY_SIGNALS = [
    "lembrar", "memória", "memoria", "decisão anterior", "o que fizemos",
    "histórico", "histórico", "conclusão", "resumo do projeto",
]
_SYSTEM_SIGNALS = [
    "zip", "compactar", "deploy", "executar", "rodar", "terminal",
    "comando", "npm", "pip install", "git ",
]
_ANALYSIS_SIGNALS = [
    "analisar", "analise", "arquitetura", "riscos", "roadmap", "dependências",
    "qualidade", "revisar", "review", "lint",
]
_LIGHTWEIGHT_SIGNALS = [
    "oi", "olá", "obrigado", "ajuda", "como", "o que é", "explicar",
    "dúvida", "duvida", "sim", "não", "ok", "entendi",
]


@dataclass
class RouteDecision:
    """Decisão do roteador: qual capability e se precisa planner."""
    target: str  # heathcliff | yui | rag_engine | execution_graph
    capability_type: str  # code_generation | memory_query | system_action | analysis | lightweight
    skip_planner: bool  # True = fluxo direto, sem planner pesado
    confidence: float
    reason: str
    meta: Dict[str, Any] = field(default_factory=dict)


def _score_signals(text: str, signals: List[str]) -> float:
    """Score 0-1 baseado em matches."""
    if not text or not signals:
        return 0.0
    lower = text.lower().strip()
    matches = sum(1 for s in signals if s.lower() in lower)
    return min(1.0, matches * 0.35) if matches else 0.0


def _route_by_intention(intention: str) -> Optional[RouteDecision]:
    """Roteamento rápido por intenção (infer_intention)."""
    if not intention or intention == "chat":
        return None
    if intention == "criar_projeto":
        return RouteDecision(
            target="heathcliff",
            capability_type="code_generation",
            skip_planner=False,
            confidence=0.9,
            reason="criar_projeto → Heathcliff + Execution Graph",
        )
    if intention == "analisar_codigo":
        return RouteDecision(
            target="heathcliff",
            capability_type="analysis",
            skip_planner=True,
            confidence=0.85,
            reason="analisar_codigo → Heathcliff (tool direto)",
        )
    if intention == "analisar_projeto":
        return RouteDecision(
            target="heathcliff",
            capability_type="analysis",
            skip_planner=True,
            confidence=0.85,
            reason="analisar_projeto → Heathcliff (tool direto)",
        )
    return None


def route(
    user_message: str,
    intention: Optional[str] = None,
    action: Optional[str] = None,
    tool_hint: Optional[str] = None,
) -> RouteDecision:
    """
    Roteia a intenção para a melhor capability.

    Args:
        user_message: mensagem do usuário
        intention: intenção inferida (infer_intention)
        action: ação do Action Engine (route_action)
        tool_hint: ferramenta sugerida

    Returns:
        RouteDecision com target, capability_type, skip_planner, etc.
    """
    msg = (user_message or "").strip().lower()
    if not msg:
        return RouteDecision(
            target="yui",
            capability_type="lightweight",
            skip_planner=True,
            confidence=0.5,
            reason="Mensagem vazia → Yui",
        )

    # 1) Tentar por intenção
    if intention:
        dec = _route_by_intention(intention)
        if dec:
            return dec

    # 2) Heurísticas por sinais
    scores = {
        "code_generation": _score_signals(msg, _CODE_SIGNALS),
        "memory_query": _score_signals(msg, _MEMORY_SIGNALS),
        "system_action": _score_signals(msg, _SYSTEM_SIGNALS),
        "analysis": _score_signals(msg, _ANALYSIS_SIGNALS),
        "lightweight": _score_signals(msg, _LIGHTWEIGHT_SIGNALS),
    }

    best_type = max(scores, key=lambda k: scores[k])
    conf = scores[best_type]

    # Lightweight: conversa simples
    if best_type == "lightweight" and conf >= 0.3:
        return RouteDecision(
            target="yui",
            capability_type="lightweight",
            skip_planner=True,
            confidence=conf,
            reason="Conversa simples → Yui (sem planner)",
        )

    # Memory: RAG direto
    if best_type == "memory_query" and conf >= 0.3:
        return RouteDecision(
            target="rag_engine",
            capability_type="memory_query",
            skip_planner=True,
            confidence=conf,
            reason="Consulta de memória → RAG Engine",
        )

    # System: execution graph
    if best_type == "system_action" and conf >= 0.3:
        return RouteDecision(
            target="execution_graph",
            capability_type="system_action",
            skip_planner=False,
            confidence=conf,
            reason="Ação de sistema → Execution Graph",
        )

    # Analysis: Heathcliff
    if best_type == "analysis" and conf >= 0.3:
        return RouteDecision(
            target="heathcliff",
            capability_type="analysis",
            skip_planner=True,
            confidence=conf,
            reason="Análise → Heathcliff (tool direto)",
        )

    # Code: Heathcliff
    if best_type == "code_generation" and conf >= 0.3:
        return RouteDecision(
            target="heathcliff",
            capability_type="code_generation",
            skip_planner=False,
            confidence=conf,
            reason="Geração de código → Heathcliff",
        )

    # Default: Yui com planner
    return RouteDecision(
        target="yui",
        capability_type="general",
        skip_planner=False,
        confidence=0.5,
        reason="Sem match claro → Yui (general)",
    )


def get_routing_display(decision: RouteDecision) -> str:
    """Retorna texto para exibição na UI (System Activity)."""
    labels = {
        "heathcliff": "Heathcliff (Engineering)",
        "yui": "Yui Core (General)",
        "rag_engine": "Memory Engine",
        "execution_graph": "Execution Graph",
    }
    target = labels.get(decision.target, decision.target)
    skip = "skip planner" if decision.skip_planner else ""
    return f"→ {target}" + (f" ({skip})" if skip else "")
