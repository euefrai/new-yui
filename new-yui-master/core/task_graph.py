# ==========================================================
# YUI TASK GRAPH
# Intenção → tarefas → subtarefas → ferramentas.
# Base para automação multi-step e agente autônomo.
# ==========================================================

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from core.capabilities import is_enabled


@dataclass
class TaskStep:
    """Uma etapa do grafo: nome, tipo (tool/action), argumentos e action opcional."""
    id: str
    name: str
    kind: str  # "tool" | "action" | "subtask"
    args: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)  # ids de steps anteriores
    action: Optional[Callable[..., Any]] = None  # função a executar (opcional; tools usam run_tool)


# Alias para compatibilidade com o conceito "Task(name, action)"
Task = TaskStep


@dataclass
class TaskGraph:
    """Grafo de tarefas para uma intenção."""
    intention: str
    steps: List[TaskStep] = field(default_factory=list)
    status: str = "pending"  # pending | running | done | failed


# Mapeamento intenção → sequência de steps (heurístico; pode ser evoluído por IA)
INTENTION_TEMPLATES: Dict[str, List[Dict[str, Any]]] = {
    "criar_projeto": [
        {"id": "t1", "name": "gerar_estrutura", "kind": "action"},
        {"id": "t2", "name": "criar_projeto_arquivos", "kind": "tool", "args_key": "root_dir,files"},
        {"id": "t3", "name": "criar_zip_projeto", "kind": "tool", "args_key": "root_dir,zip_name", "depends_on": ["t2"]},
        {"id": "t4", "name": "validar", "kind": "action", "depends_on": ["t3"]},
    ],
    "analisar_codigo": [
        {"id": "t1", "name": "analisar_arquivo", "kind": "tool", "args_key": "filename,content"},
    ],
    "analisar_projeto": [
        {"id": "t1", "name": "analisar_projeto", "kind": "tool", "args_key": "raiz"},
    ],
}


def infer_intention(user_message: str) -> str:
    """Infere a intenção principal a partir da mensagem (heurístico)."""
    t = (user_message or "").lower().strip()
    # Criar projeto (calculadora, login, sistema, api, etc.)
    if any(x in t for x in ("criar", "cria", "gerar", "fazer")):
        if any(x in t for x in ("calculadora", "login", "sistema", "api", "projeto", "site")):
            return "criar_projeto"
    # Analisar
    if "analis" in t or "analise" in t:
        if "arquivo" in t or "código" in t or "codigo" in t:
            return "analisar_codigo"
        if "projeto" in t:
            return "analisar_projeto"
    return "chat"


def build_task_graph(intention: str, user_message: str) -> TaskGraph:
    """
    Constrói um grafo de tarefas para a intenção.
    Se capabilities["planner"] estiver off, retorna grafo vazio (engine segue fluxo normal).
    """
    if not is_enabled("planner"):
        return TaskGraph(intention=intention, steps=[])
    template = INTENTION_TEMPLATES.get(intention)
    if not template:
        return TaskGraph(intention=intention, steps=[])
    steps = []
    for t in template:
        step = TaskStep(
            id=t["id"],
            name=t["name"],
            kind=t["kind"],
            args=t.get("args", {}),
            depends_on=t.get("depends_on", []),
        )
        steps.append(step)
    return TaskGraph(intention=intention, steps=steps)


def get_planned_steps_for_prompt(task_graph: TaskGraph) -> str:
    """Retorna texto do plano para injetar no prompt da IA (multi-step)."""
    if not task_graph.steps:
        return ""
    lines = ["Plano de execução (tarefas em ordem):"]
    for s in task_graph.steps:
        dep = f" (depende de {', '.join(s.depends_on)})" if s.depends_on else ""
        lines.append(f"  - {s.id}: {s.name} ({s.kind}){dep}")
    return "\n".join(lines)


def next_step(task_graph: TaskGraph) -> Optional[TaskStep]:
    """Retorna o próximo step a executar (quando status=pending, retorna o primeiro)."""
    if not task_graph.steps or task_graph.status != "pending":
        return None
    return task_graph.steps[0]
