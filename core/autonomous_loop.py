# ==========================================================
# YUI AUTONOMOUS LOOP (leve)
# Ciclo opcional: ver objetivos → escolher prioritário → mini plano → 1 passo → parar.
# max_auto_steps=1: NUNCA rodar infinito (Render/Zeabur sem freio = servidor morto).
# ==========================================================

from typing import Any, Dict, List, Optional

from core.goals.goal_manager import Goal, get_active_goals, goals_to_context
from core.planner import PlanStep, criar_plano_estruturado

MAX_AUTO_STEPS = 1


def run_one_autonomous_step(
    user_id: str = "",
    chat_id: str = "",
) -> Optional[Dict[str, Any]]:
    """
    Executa no máximo 1 passo autônomo.
    Retorna {goal, plan_step, executed} ou None se não houver objetivo ativo.
    O EXECUTOR deve executar o step — este módulo só planeja.
    """
    goals = get_active_goals(user_id, chat_id)
    if not goals:
        return None

    goal = goals[0]
    # Cria mini plano baseado no objetivo
    plan = criar_plano_estruturado(
        mensagem=goal.name,
        user_id=user_id,
        chat_id=chat_id,
        max_steps=MAX_AUTO_STEPS,
    )
    if not plan:
        return None

    step = plan[0]
    return {
        "goal": goal,
        "plan_step": step,
        "executed": False,
    }
