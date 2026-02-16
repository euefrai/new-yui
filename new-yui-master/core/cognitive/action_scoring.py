"""
Action Scoring System — Micro-RL sem treinar modelo.

Pontuação por ação:
+3 resolveu erro
+2 reduziu código / criou arquivo útil
+1 ação concluída com sucesso
0 neutro
-1 criou warning / execução lenta
-2 ação redundante / loop
-3 causou crash / erro grave
"""

from typing import Dict, Optional

# Pontuação por tipo de resultado
SCORE_RESOLVED_ERROR = 3
SCORE_REDUCED_CODE = 2
SCORE_SUCCESS = 1
SCORE_NEUTRAL = 0
SCORE_WARNING = -1
SCORE_LOOP_REDUNDANT = -2
SCORE_CRASH = -3

# Histórico de scores (janela móvel)
_scores: list = []
_max_scores = 50


def score_action(
    tool_name: str,
    ok: bool,
    had_error: bool = False,
    resolved_error: bool = False,
    files_created: int = 0,
    loop_detected: bool = False,
    ram_impact: str = "low",
) -> int:
    """
    Calcula e registra pontuação da ação.

    Returns:
        score aplicado
    """
    global _scores
    score = SCORE_NEUTRAL

    if resolved_error:
        score = SCORE_RESOLVED_ERROR
    elif had_error:
        score = SCORE_CRASH if "crash" in str(had_error).lower() or not ok else SCORE_WARNING
    elif loop_detected:
        score = SCORE_LOOP_REDUNDANT
    elif ok:
        if files_created > 0 and tool_name in ("fs_create_file", "criar_projeto_arquivos"):
            score = SCORE_REDUCED_CODE
        else:
            score = SCORE_SUCCESS

    if ram_impact == "high":
        score = max(SCORE_CRASH, score - 1)

    _scores.append(score)
    if len(_scores) > _max_scores:
        _scores = _scores[-_max_scores:]
    return score


def get_action_score() -> int:
    """Retorna score da última ação."""
    return _scores[-1] if _scores else SCORE_NEUTRAL


def get_average_score() -> float:
    """Média dos últimos scores."""
    if not _scores:
        return 0.0
    return sum(_scores) / len(_scores)


def get_cognitive_status() -> Dict:
    """
    Status para o painel de Observability.

    Returns:
        planner_confidence, last_action_score, ram_impact, score_letter
    """
    last = get_action_score()
    avg = get_average_score()

    # Mapeamento score → letra (A+ a F)
    if last >= 2:
        letter = "A+"
    elif last == 1:
        letter = "A"
    elif last == 0:
        letter = "B"
    elif last == -1:
        letter = "C"
    elif last == -2:
        letter = "D"
    else:
        letter = "F"

    # Planner confidence (0-100) baseado na média
    confidence = max(0, min(100, int(50 + avg * 25)))

    return {
        "planner_confidence": confidence,
        "last_action_score": letter,
        "last_action_score_raw": last,
        "average_score": round(avg, 2),
        "recent_scores_count": len(_scores),
    }
