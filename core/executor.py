# ==========================================================
# YUI EXECUTOR (v2)
# Loop de execução: for step in plan -> executar -> salvar estado.
# Não faz tudo de uma vez; age passo a passo.
# Pode parar se algo der errado.
# Energy-aware: para execução se energia acabar.
# ==========================================================

from typing import Any, Callable, Dict, List, Optional

from core.event_bus import emit
from core.planner import PlanStep
from core.self_state import set_last_action, set_last_error
from core.tool_runner import run_tool

try:
    from core.energy_manager import get_energy_manager, COST_TOOL
except ImportError:
    get_energy_manager = None
    COST_TOOL = 15


def executar_step(
    step: PlanStep,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Executa uma única etapa do plano.
    Retorna {ok, result, error, stop} — stop=True se deve parar o loop.
    """
    if get_energy_manager:
        em = get_energy_manager()
        if not em.can_execute():
            return {"ok": False, "result": None, "error": "Energia esgotada.", "stop": True}
        em.consume(COST_TOOL if step.tool else 3)
    ctx = context or {}
    if step.tool:
        result = run_tool(step.tool, {**step.args, **ctx})
        emit("tool_executed", tool_name=step.tool, args=step.args, result=result)
        if not result.get("ok"):
            set_last_error(result.get("error") or "erro desconhecido")
            return {"ok": False, "result": result, "error": result.get("error"), "stop": True}
        set_last_action(f"tool:{step.tool}")
        return {"ok": True, "result": result, "error": None, "stop": False}
    # action sem tool (ex: gerar_estrutura, validar) — delegado ao caller
    set_last_action(f"action:{step.action}")
    return {"ok": True, "result": None, "error": None, "stop": False}


def executar_plano(
    plan: List[PlanStep],
    context: Optional[Dict[str, Any]] = None,
    on_step: Optional[Callable[[PlanStep, Dict], None]] = None,
    max_steps: int = 5,
) -> List[Dict[str, Any]]:
    """
    Executa o plano passo a passo.
    Para no primeiro erro se result["stop"] for True.
    on_step: callback opcional após cada step (para acumular context).
    """
    results: List[Dict[str, Any]] = []
    ctx = dict(context or {})

    for i, step in enumerate(plan):
        if i >= max_steps:
            break
        if get_energy_manager and not get_energy_manager().can_execute():
            break
        out = executar_step(step, ctx)
        results.append(out)
        if on_step:
            on_step(step, out)
        payload = out.get("result")
        if payload and isinstance(payload, dict) and payload.get("ok") and payload.get("result"):
            ctx.update(payload.get("result") if isinstance(payload["result"], dict) else {})
        if out.get("stop"):
            break
    return results
