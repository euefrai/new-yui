# ==========================================================
# YUI CONFIDENCE ENGINE
# Roteamento inteligente por confiança — ranking de agentes.
#
# Antes: Intent → Registry → 1 agente (tudo ou nada)
# Depois: Intent → Registry → Ranking → Melhor decisão
#
# Benefícios:
# - Ativa menos módulos pesados (menos RAM)
# - Evita decisões erradas do router
# - Prepara terreno para multi-agente real
# ==========================================================

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

DEFAULT_THRESHOLD = 0.4
FALLBACK_AGENT = "yui"


@dataclass
class Intent:
    """Intent simplificado para scoring."""
    type: str  # capability_type: code_generation, memory_query, etc.
    context: Optional[str] = None  # tool_hint, contexto extra
    priority_hint: Optional[str] = None  # histórico/memória


class ConfidenceEngine:
    """
    Roteamento probabilístico — ranking de skills por score.

    score(intent, skills) → lista ordenada por confiança
    best_agent(ranked, threshold=0.4) → agente ou fallback
    """

    def __init__(self, threshold: float = DEFAULT_THRESHOLD):
        self.threshold = threshold

    def score(self, intent: Intent, skills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Pontua skills para o intent. Retorna ranking decrescente.

        Criterios:
        - match por tag: +0.6
        - match por contexto: +0.2
        - match por priority: +0.2
        """
        results = []
        intent_type = (intent.type or "").lower().strip()
        intent_context = (intent.context or "").lower().strip()
        intent_priority = (intent.priority_hint or "").lower().strip()

        for skill in skills:
            score = 0.0

            # match por tag
            tags = [t.lower() for t in skill.get("tags", [])]
            if intent_type in tags:
                score += 0.6

            # match por contexto (skill meta ou tags)
            context_tags = skill.get("meta", {}).get("context", [])
            if isinstance(context_tags, str):
                context_tags = [context_tags]
            context_tags = [str(c).lower() for c in context_tags]
            if intent_context and (intent_context in context_tags or any(intent_context in t for t in tags)):
                score += 0.2

            # match por priority (meta do skill)
            priority = skill.get("meta", {}).get("priority", 0)
            if isinstance(priority, (int, float)) and priority > 0:
                score += min(0.2, priority * 0.1)
            elif intent_priority and skill.get("name", "").lower() in intent_priority:
                score += 0.2

            # bonus por skip_planner quando intent é leve
            if intent_type in ("lightweight", "chat", "general") and skill.get("skip_planner"):
                score += 0.1

            results.append({
                "agent": skill["agent"],
                "name": skill.get("name", ""),
                "score": min(1.0, score),
                "skip_planner": skill.get("skip_planner", False),
            })

        return sorted(results, key=lambda x: x["score"], reverse=True)

    def best_agent(
        self,
        ranked: List[Dict[str, Any]],
        threshold: Optional[float] = None,
        fallback: str = FALLBACK_AGENT,
    ) -> Dict[str, Any]:
        """
        Retorna o melhor agente ou fallback se score < threshold.

        Returns:
            {"agent": str, "score": float, "skip_planner": bool, "used_fallback": bool}
        """
        th = threshold if threshold is not None else self.threshold
        if not ranked:
            return {"agent": fallback, "score": 0.0, "skip_planner": True, "used_fallback": True}

        best = ranked[0]
        if best["score"] < th:
            return {
                "agent": fallback,
                "score": best["score"],
                "skip_planner": True,
                "used_fallback": True,
            }
        return {**best, "used_fallback": False}


_engine: Optional[ConfidenceEngine] = None


def get_confidence_engine(threshold: float = DEFAULT_THRESHOLD) -> ConfidenceEngine:
    """Retorna o ConfidenceEngine singleton."""
    global _engine
    if _engine is None:
        _engine = ConfidenceEngine(threshold=threshold)
    return _engine
