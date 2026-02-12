# ==========================================================
# YUI CAPABILITY ROUTER
# Roteador de habilidades — decide qual módulo deve resolver.
#
# Antes do planner: Intent → Capability Router → Skill Registry → melhor módulo
# Router NÃO conhece agentes. Router consulta Registry.
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
    """Roteamento rápido por intenção (infer_intention). Consulta Skill Registry."""
    if not intention or intention == "chat":
        return None
    cap_type = {
        "criar_projeto": "code_generation",
        "analisar_codigo": "analysis",
        "analisar_projeto": "analysis",
    }.get(intention)
    if not cap_type:
        return None
    try:
        from core.skills.registry import find_skill
        skill = find_skill(cap_type)
        if skill:
            return RouteDecision(
                target=skill.agent,
                capability_type=cap_type,
                skip_planner=skill.skip_planner,
                confidence=0.9 if intention == "criar_projeto" else 0.85,
                reason=f"{intention} → Registry: {skill.name}",
            )
    except Exception:
        pass
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

    # Confidence Engine — ranking de skills
    if conf >= 0.3:
        try:
            from core.skills.registry import get_all_skills
            from core.router.confidence_engine import get_confidence_engine, Intent

            skills = get_all_skills()
            engine = get_confidence_engine(threshold=0.4)
            intent = Intent(
                type=best_type,
                context=tool_hint,
                priority_hint=None,
            )
            ranked = engine.score(intent, skills)
            best = engine.best_agent(ranked, threshold=0.4, fallback="yui")

            if not best["used_fallback"]:
                return RouteDecision(
                    target=best["agent"],
                    capability_type=best_type,
                    skip_planner=best["skip_planner"],
                    confidence=max(conf, best["score"]),
                    reason=f"Confidence: {best.get('name', best['agent'])} (score={best['score']:.2f})",
                )
        except Exception:
            pass

    # Fallback: default mapping (quando confidence < threshold)
    _fallback = {
        "lightweight": ("yui", True),
        "memory_query": ("rag_engine", True),
        "system_action": ("execution_graph", False),
        "analysis": ("heathcliff", True),
        "code_generation": ("heathcliff", False),
    }
    target, skip = _fallback.get(best_type, ("yui", False))
    return RouteDecision(
        target=target,
        capability_type=best_type if conf >= 0.3 else "general",
        skip_planner=skip,
        confidence=conf,
        reason=("Registry fallback" if conf >= 0.3 else "Sem match") + f" → {target}",
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
