# ==========================================================
# YUI ATTENTION MANAGER
# Filtro cognitivo: decide o que importa antes de ir pro planner.
# Prioridade + recência + tipo de tarefa — não tamanho.
# ==========================================================

from typing import Any, Dict, List, Optional

try:
    from core.energy_manager import get_energy_manager
except ImportError:
    get_energy_manager = None

DEFAULT_TOP = 5
TOP_ENERGY_LOW = 3
TOP_ENERGY_NORMAL = 8


def score(item: Dict[str, Any]) -> float:
    """
    Pontua um item de contexto.
    Usa: prioridade, recência, tipo de tarefa — nunca só len(texto).
    """
    priority = float(item.get("priority", 1.0))
    recent = item.get("recent", False)
    task_relevant = item.get("task_relevant", False)

    score_val = priority
    if recent:
        score_val += 2
    if task_relevant:
        score_val += 1.5
    return score_val


def select(items: List[Dict[str, Any]], top: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Seleciona os top-N itens mais relevantes por score.
    Se top não informado, usa energia: baixa -> 3, normal -> 8.
    """
    if top is None and get_energy_manager:
        em = get_energy_manager()
        top = TOP_ENERGY_LOW if em.is_low() else TOP_ENERGY_NORMAL
    top = top or DEFAULT_TOP

    scored = [(score(it), it) for it in items]
    scored.sort(key=lambda x: -x[0])
    return [it for _, it in scored[:top]]


def filter_context_blocks(
    ctx: Dict[str, Any],
    user_message: str = "",
    top: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Converte contexto bruto em itens, pontua, filtra e devolve contexto enxuto.
    Blocos: historico, contexto_projeto, memoria_vetorial, contexto_chat_anterior, memoria_eventos.
    system_state e user_profile: sempre incluídos (pequenos e essenciais).
    """
    t = (user_message or "").lower()
    items: List[Dict[str, Any]] = []

    # Histórico: sempre incluso (essencial para conversa)
    # user_profile e system_state: sempre incluídos no final

    # Memória vetorial: relevante à pergunta (já foi buscada por similaridade)
    if ctx.get("memoria_vetorial"):
        items.append({
            "key": "memoria_vetorial",
            "content": ctx["memoria_vetorial"],
            "priority": 3,
            "recent": True,
            "task_relevant": True,
        })

    # Contexto do projeto: útil para criacão/analise
    if ctx.get("contexto_projeto"):
        rel = any(x in t for x in ("criar", "analis", "projeto", "arquivo", "código", "codigo"))
        items.append({
            "key": "contexto_projeto",
            "content": ctx["contexto_projeto"],
            "priority": 2 if rel else 1,
            "recent": False,
            "task_relevant": rel,
        })

    # Contexto chat anterior
    if ctx.get("contexto_chat_anterior"):
        items.append({
            "key": "contexto_chat_anterior",
            "content": ctx["contexto_chat_anterior"],
            "priority": 2,
            "recent": True,
            "task_relevant": True,
        })

    # Memória de eventos
    if ctx.get("memoria_eventos"):
        items.append({
            "key": "memoria_eventos",
            "content": ctx["memoria_eventos"],
            "priority": 1.5,
            "recent": True,
            "task_relevant": False,
        })

    selected = select(items, top=top)
    out = {k: "" if k != "historico" else [] for k in ctx}
    out["historico"] = ctx.get("historico", [])
    out["user_profile"] = ctx.get("user_profile", {})
    out["system_state"] = ctx.get("system_state", "")

    for it in selected:
        key = it.get("key")
        if key:
            val = it.get("content", ctx.get(key, [] if key == "historico" else ""))
            out[key] = val

    return out


def filter_tools_by_intention(tool_names: List[str], intention: str) -> List[str]:
    """
    Filtra tools por intenção.
    Se intenção é código: create_file, zip, analisar...
    Não carrega tools irrelevantes (ex: voz, imagem se não for o caso).
    """
    t = (intention or "").lower()
    if not t:
        return tool_names

    code_tools = {"analisar_arquivo", "criar_projeto_arquivos", "criar_zip_projeto", "ler_arquivo_texto", "listar_arquivos"}
    project_tools = {"analisar_projeto", "observar_ambiente", "consultar_indice_projeto"}
    time_tools = {"get_current_time"}
    search_tools = {"buscar_web"}

    if any(x in t for x in ("horas", "hora", "data", "dia", "bom dia", "boa tarde", "boa noite", "agora", "timestamp")):
        return [n for n in tool_names if n in time_tools] or list(tool_names)
    if any(x in t for x in ("buscar", "pesquisar", "verificar", "informação", "notícia", "clima")):
        return [n for n in tool_names if n in search_tools] or list(tool_names)
    if any(x in t for x in ("criar", "gerar", "projeto", "calculadora", "login", "código")):
        return [n for n in tool_names if n in code_tools or n in project_tools]
    if any(x in t for x in ("analis", "analise")):
        return [n for n in tool_names if n in project_tools or n == "analisar_arquivo"]
    if any(x in t for x in ("ler", "arquivo", "listar")):
        return [n for n in tool_names if n in {"ler_arquivo_texto", "listar_arquivos"}]
    return tool_names
