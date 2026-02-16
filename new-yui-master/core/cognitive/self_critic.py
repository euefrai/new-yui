"""
Self-Critic — Avalia a qualidade da execução.

Não gera código. Avalia:
- a ação foi eficiente?
- gerou erro?
- abriu loops desnecessários?
- aumentou RAM?
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.cognitive.observer import Observation
from core.cognitive.action_scoring import score_action, SCORE_CRASH, SCORE_LOOP_REDUNDANT, SCORE_RESOLVED_ERROR, SCORE_SUCCESS, SCORE_WARNING


@dataclass
class CritiqueResult:
    """Resultado da avaliação do Self-Critic."""
    efficient: bool
    had_error: bool
    loop_detected: bool
    ram_impact: str  # low | medium | high
    score: int
    feedback: str


def criticize(
    obs: Optional[Observation],
    last_action: str = "",
    last_error: str = "",
    loop_detected: bool = False,
    tools_ok: bool = True,
) -> CritiqueResult:
    """
    Avalia o turno executado.

    Args:
        obs: observação do Observer
        last_action: última ação (tool:xxx ou answer)
        last_error: último erro registrado
        loop_detected: se metacognition detectou loop
        tools_ok: se todas as tools retornaram ok

    Returns:
        CritiqueResult com avaliação
    """
    had_error = bool(last_error)
    resolved_error = False
    files_created = 0

    if obs:
        had_error = had_error or bool(obs.errors_detected)
        files_created = len(obs.files_altered)

    # RAM impact (heurística: muitas tools = mais RAM)
    ram_impact = "low"
    if obs and len(obs.tools_executed) > 5:
        ram_impact = "high"
    elif obs and len(obs.tools_executed) > 2:
        ram_impact = "medium"

    # Score
    tool_name = last_action.replace("tool:", "").replace("skill:", "").strip()
    score = score_action(
        tool_name=tool_name or "answer",
        ok=tools_ok and not had_error,
        had_error=had_error,
        resolved_error=resolved_error,
        files_created=files_created,
        loop_detected=loop_detected,
        ram_impact=ram_impact,
    )

    # Feedback
    if loop_detected:
        feedback = "Loop detectado. Evite repetir ações."
    elif had_error:
        feedback = "Erro na execução. Considere abordagem alternativa."
    elif score >= SCORE_SUCCESS:
        feedback = "Execução adequada."
    else:
        feedback = "Execução subótima. Revise estratégia."

    return CritiqueResult(
        efficient=score >= 0,
        had_error=had_error,
        loop_detected=loop_detected,
        ram_impact=ram_impact,
        score=score,
        feedback=feedback,
    )
