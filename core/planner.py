# ==========================================================
# YUI PLANNER CORE (v2)
# A IA não responde direto: primeiro cria um plano estruturado.
# Com Goal System: planner(input, goals_ativos) — objetivos mudam a tomada de decisão.
# ==========================================================

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from core.capabilities import is_enabled
from core.limits import MAX_STEPS as LIMIT_MAX_STEPS
from core.tool_schema import TOOL_SCHEMAS, get_schema

try:
    from core.energy_manager import get_energy_manager
except ImportError:
    get_energy_manager = None
try:
    from core.identity_core import get_identity_core
except ImportError:
    get_identity_core = None
try:
    from core.reflection_loop import get_estado_reflexao
except ImportError:
    get_estado_reflexao = lambda: "ok"

if TYPE_CHECKING:
    from core.goals.goal_manager import Goal

# Fail safe: limites para evitar travamento
MAX_STEPS = 5
MAX_PLAN_LENGTH = 8


@dataclass
class PlanStep:
    """Uma etapa do plano: objetivo, ação, tool opcional."""
    goal: str
    action: str
    tool: Optional[str] = None
    args: Dict[str, Any] = field(default_factory=dict)


def _buscar_memoria_relevante(user_id: str, chat_id: str, mensagem: str) -> str:
    """Memory aware: busca histórico antes de planejar."""
    if not is_enabled("memory"):
        return ""
    try:
        from core.memory_manager import build_context_text
        ctx = build_context_text(user_id=user_id, chat_id=chat_id, limit_short=5, limit_long=5)
        return ctx or ""
    except Exception:
        return ""


def _mapear_intencao_tools(intencao: str) -> List[str]:
    """Tool reasoning: mapeia intenção para tools sugeridas."""
    t = intencao.lower()
    tools = []
    if "criar" in t or "gerar" in t or "projeto" in t:
        tools.extend(["criar_projeto_arquivos", "criar_zip_projeto"])
    if "analis" in t or "analise" in t:
        if "arquivo" in t or "código" in t or "codigo" in t:
            tools.append("analisar_arquivo")
        else:
            tools.extend(["analisar_projeto", "observar_ambiente"])
    if "ler" in t or "arquivo" in t:
        tools.extend(["ler_arquivo_texto", "listar_arquivos"])
    if "consultar" in t or "índice" in t or "indice" in t:
        tools.append("consultar_indice_projeto")
    return list(dict.fromkeys(tools))  # remove duplicatas


def criar_plano_estruturado(
    mensagem: str,
    user_id: str = "",
    chat_id: str = "",
    max_steps: Optional[int] = None,
    goals_ativos: Optional[List["Goal"]] = None,
) -> List[PlanStep]:
    """
    Cria planos estruturados multi-etapas.
    Memory aware: usa histórico se falhou antes (ex: zip).
    Tool reasoning: escolhe tools baseado na intenção.
    Goals aware: objetivos ativos influenciam priorização.
    Energy aware: energia < 20 → plano simples (menos steps).
    Fail safe: respeita max_steps.
    """
    if not is_enabled("planner"):
        return []

    max_steps = max_steps or LIMIT_MAX_STEPS
    if get_identity_core:
        max_steps = min(max_steps, get_identity_core().get_max_plan_steps())
    if get_energy_manager:
        em = get_energy_manager()
        if em.is_low():
            max_steps = min(max_steps, 2)
    # Reflection Loop: adapta ao estado do servidor
    estado_reflexao = get_estado_reflexao()
    if estado_reflexao == "modo_economia":
        max_steps = min(max_steps, 2)
    elif estado_reflexao == "dividir_tasks":
        max_steps = min(max_steps, 3)
    memory = _buscar_memoria_relevante(user_id, chat_id, mensagem)
    tools_sugeridas = _mapear_intencao_tools(mensagem)

    # Ajuste por memória: se falhou antes em zip, evita dependência
    skip_zip = "zip" in (memory or "").lower() and "falhou" in (memory or "").lower()
    # Reflection Loop: modo economia → evita zip (pesado)
    if estado_reflexao == "modo_economia":
        skip_zip = True

    steps: List[PlanStep] = []
    t = (mensagem or "").lower()

    # Criar projeto
    if any(x in t for x in ("criar", "cria", "gerar", "projeto", "calculadora", "login", "sistema")):
        steps.append(PlanStep(goal="Estruturar projeto", action="gerar_estrutura", tool=None))
        steps.append(PlanStep(goal="Criar arquivos", action="criar", tool="criar_projeto_arquivos"))
        if not skip_zip:
            steps.append(PlanStep(goal="Compactar", action="zipar", tool="criar_zip_projeto"))
        steps.append(PlanStep(goal="Validar", action="validar", tool=None))

    # Analisar código
    elif "analis" in t and ("arquivo" in t or "código" in t or "codigo" in t):
        steps.append(PlanStep(goal="Analisar código", action="analisar", tool="analisar_arquivo"))

    # Analisar projeto
    elif "analis" in t and "projeto" in t:
        steps.append(PlanStep(goal="Analisar projeto", action="analisar", tool="analisar_projeto"))

    # Observar ambiente
    elif "observar" in t or "visão" in t or "visao" in t:
        steps.append(PlanStep(goal="Observar ambiente", action="observar", tool="observar_ambiente"))

    # Fallback: resposta direta
    if not steps:
        steps.append(PlanStep(goal="Interpretar pedido", action="responder", tool=None))
        steps.append(PlanStep(goal="Gerar resposta", action="responder", tool=None))

    # Identity: risk_tolerance low → remove steps com tools pesadas
    if get_identity_core:
        identity = get_identity_core()
        steps = [s for s in steps if not s.tool or identity.is_tool_allowed(s.tool)]

    # Fail safe: corta plano se exceder limite
    return steps[:min(max_steps, MAX_PLAN_LENGTH)]


def plan_to_prompt(plan: List[PlanStep], goals_ativos: Optional[List["Goal"]] = None) -> str:
    """Converte plano em texto para injetar no prompt da IA. Inclui goals se houver."""
    parts = []
    if goals_ativos:
        try:
            from core.goals.goal_manager import goals_to_context
            ctx = goals_to_context(goals_ativos)
            if ctx:
                parts.append(ctx)
                parts.append("")
        except Exception:
            pass
    if plan:
        lines = ["Plano de execução (etapas em ordem):"]
        for i, s in enumerate(plan, 1):
            t = f"  {i}. {s.goal} -> {s.action}"
            if s.tool:
                t += f" (tool: {s.tool})"
            lines.append(t)
        parts.append("\n".join(lines))
    return "\n".join(parts) if parts else ""
