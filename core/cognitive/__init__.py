"""
Cognitive Loop — Metabolismo da Yui.

Executor → Observer → Self-Critic → Memory Update

- observer: registra tempo, tokens, arquivos, erros, impacto
- self_critic: avalia eficiência, erros, loops, RAM
- action_scoring: pontuação por ação (micro-RL)
"""

from core.cognitive.observer import observe_turn, Observation, get_last_observation
from core.cognitive.self_critic import criticize, CritiqueResult
from core.cognitive.action_scoring import score_action, get_action_score, get_cognitive_status

__all__ = [
    "observe_turn",
    "Observation",
    "get_last_observation",
    "criticize",
    "CritiqueResult",
    "score_action",
    "get_action_score",
    "get_cognitive_status",
]
