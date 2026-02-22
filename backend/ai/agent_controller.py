# ==========================================================
# YUI - AGENT CONTROLLER
# Cérebro central da IA: só ele conversa com a IA, decide
# tools, memória e resposta final. O frontend nunca recebe JSON cru.
# ==========================================================

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from openai import OpenAI

from yui_ai.services.memory_service import save_message
from core.capabilities import is_enabled
from core.event_bus import emit
from core.memory_manager import add_event
from core.self_state import set_last_action, set_last_error, set_confidence
from core.tool_runner import run_tool
from core.task_engine import get_task_engine
from core.action_planner import get_action_planner
from core.user_profile import get_user_profile

from backend.ai.auto_debug import auto_debug
from backend.ai.context_engine import montar_contexto_ia
from core.memoria_ia import salvar_resumo as salvar_memoria_ia
from backend.ai.context_memory import salvar_memoria as salvar_memoria_chat
from backend.ai.self_reflect import avaliar_resposta
from backend.ai.skill_manager import executar_skill, listar_skills
from backend.ai.task_planner import criar_plano
from backend.ai.tool_router import processar_resposta_ai
from core.limits import MAX_STEPS as LIMIT_MAX_STEPS
from core.usage_tracker import record_response_cost, estimate_cost_brl, BUDGET_ALERT_BRL
from core.goals.goal_manager import get_active_goals, update_progress
from core.planner import criar_plano_estruturado, plan_to_prompt
try:
    from core.attention_manager import filter_context_blocks, filter_tools_by_intention
except ImportError:
    filter_context_blocks = None
    filter_tools_by_intention = None
try:
    from core.identity_core import get_identity_core
except ImportError:
    get_identity_core = None
try:
    from core.metacognition import get_metacognition, MetaState, _build_state
except ImportError:
    get_metacognition = None
    MetaState = None
    _build_state = None
try:
    from core.world_model import get_world_model
except ImportError:
    get_world_model = None
try:
    from core.strategy_engine import get_strategy_engine
except ImportError:
    get_strategy_engine = None
try:
    from core.energy_manager import (
        get_energy_manager,
        COST_RESPONDER_IA,
        COST_TOOL,
        COST_PLANNER,
        COST_REFLECT,
    )
except ImportError:
    get_energy_manager = None
    COST_RESPONDER_IA = COST_TOOL = COST_PLANNER = COST_REFLECT = 0
try:
    from core.cognitive_budget import get_cognitive_budget, reset_budget_for_turn
except ImportError:
    get_cognitive_budget = None
    reset_budget_for_turn = None
try:
    from core.self_monitoring import (
        get_system_snapshot,
        should_use_fast_mode,
        get_system_state_for_prompt,
    )
except ImportError:
    get_system_snapshot = None
    should_use_fast_mode = None
    get_system_state_for_prompt = None
from core.reflection import refletir
from core.state_machine import AgentState, transition
from core.task_graph import build_task_graph, get_planned_steps_for_prompt, infer_intention
try:
    from core.arbitration_engine import decide_leader, get_hybrid_modifier
except ImportError:
    decide_leader = None
    get_hybrid_modifier = None

# ==========================================================
# CONFIG
# ==========================================================

OPENAI_API_KEY = (os.environ.get("OPENAI_API_KEY") or "").strip()
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
MODEL = os.environ.get("OPENAI_CHAT_MODEL", "gpt-5-mini")
MAX_HISTORY = 50
CHUNK_SIZE = 12  # chunks menores = streaming mais fluido  # tamanho do chunk ao “streamar” a resposta final

TOOL_DESCRIPTIONS = {
    "analisar_arquivo": "- analisar_arquivo(filename, content): quando o usuário COLAR ou descrever um código/arquivo específico.\n",
    "listar_arquivos": "- listar_arquivos(pasta, padrao, limite): listar arquivos do projeto.\n",
    "ler_arquivo_texto": "- ler_arquivo_texto(caminho, max_chars): ler conteúdo de um arquivo.\n",
    "analisar_projeto": "- analisar_projeto(raiz?): analisar arquitetura, riscos e roadmap.\n",
    "observar_ambiente": "- observar_ambiente(raiz?): visão rápida do projeto e sugestões.\n",
    "criar_projeto_arquivos": "- criar_projeto_arquivos(root_dir, files): criar projeto. files = lista [{path, content}], ex: [{\"path\":\"index.html\",\"content\":\"<html>...</html>\"}].\n",
    "criar_zip_projeto": "- criar_zip_projeto(root_dir, zip_name?): gerar script para compactar o projeto em ZIP.\n",
    "consultar_indice_projeto": "- consultar_indice_projeto(raiz?): consultar índice de arquitetura em cache.\n",
    "get_current_time": "- get_current_time(): quando o usuário perguntar as horas, data, ou para saudação (Bom dia/Boa tarde). Sempre use para horário real.\n",
    "buscar_web": "- buscar_web(query, limite?): buscar dados externos quando precisar verificar. Para perguntas gerais (feriados, datas, curiosidades), prefira mode answer com seu conhecimento — não use buscar_web.\n",
    "fs_create_file": "- fs_create_file(path, content): criar/sobrescrever arquivo no sandbox (workspace). Ex: fs_create_file(\"main.py\", \"print(1)\").\n",
    "fs_create_folder": "- fs_create_folder(path): criar pasta no sandbox. Ex: fs_create_folder(\"src/components\").\n",
    "fs_delete_file": "- fs_delete_file(path): deletar arquivo ou pasta no sandbox.\n",
    "generate_project_map": "- generate_project_map(root?): gerar .yui_map.json (estrutura e dependências).\n",
    "create_mission": "- create_mission(project, goal, tasks?): Project Brain — cria missão persistente. project=nome, goal=objetivo, tasks=lista opcional de tarefas. Use quando o usuário definir um objetivo de longo prazo.\n",
    "update_mission_progress": "- update_mission_progress(project, task_completed?, progress_delta?, current_task?): Project Brain — atualiza progresso da missão ativa após concluir uma tarefa. Use quando terminar uma etapa.\n",
}

TOOL_SYSTEM_HEADER = (
    "Você é a Yui, uma IA desenvolvedora de alto nível que responde SEMPRE em português do Brasil.\n"
    "Seja preciso, reflexiva e completa. Analise o contexto antes de responder. "
    "Para perguntas complexas, pense passo a passo. Use ferramentas quando isso enriquecer a resposta.\n\n"
    "Ferramentas disponíveis (nomes exatos):\n"
)

TOOL_SYSTEM_FOOTER = (
    "\nPlanejamento:\n"
    "- Se resolver com texto direto, responda SOMENTE um JSON:\n"
    '  {"mode":"answer","answer":"sua resposta em português aqui"}\n'
    "- Se precisar de ferramentas, responda SOMENTE um JSON:\n"
    '  {"mode":"tools","steps":[{"tool":"NOME","args":{...}}, ...], "final_answer":"(opcional) conclusão"}\n'
    "NUNCA misture texto fora do JSON. O JSON deve ser o único conteúdo da resposta."
)


def _build_tool_system(user_message: str = "") -> str:
    """Monta TOOL_SYSTEM com Attention: filtra tools por intenção (menos RAM, menos tokens)."""
    all_tools = list(TOOL_DESCRIPTIONS.keys())
    if filter_tools_by_intention:
        tools = filter_tools_by_intention(all_tools, user_message)
        if not tools:
            tools = all_tools
    else:
        tools = all_tools
    lines = [TOOL_DESCRIPTIONS.get(t, "") for t in tools if t in TOOL_DESCRIPTIONS]
    return TOOL_SYSTEM_HEADER + "".join(lines) + TOOL_SYSTEM_FOOTER

# Bloco de SKILLS (habilidades dinâmicas) — montado em tempo de execução
def _build_skills_system() -> str:
    skills = listar_skills()
    if not skills:
        return ""
    lista = "\n".join(f"- {k}: {v.get('descricao', '')}" for k, v in skills.items())
    return (
        "\n\nVocê também possui SKILLS (habilidades dinâmicas). Use quando a tarefa se encaixar.\n"
        f"SKILLS DISPONÍVEIS:\n{lista}\n\n"
        "Para usar uma skill, responda SOMENTE este JSON:\n"
        '{"usar_skill": "nome_da_skill", "dados": { ... }}\n'
        "Os dados dependem da skill (ex: calculadora usa a, b, op)."
    )


def _extract_answer_from_raw(raw: str) -> str | None:
    """Fallback: extrai 'answer' quando JSON contém mode:answer mas o parse falhou."""
    if not raw or '"answer"' not in raw:
        return None
    idx = raw.find('"answer"')
    if idx == -1:
        return None
    colon = raw.find(":", idx)
    if colon == -1:
        return None
    rest = raw[colon + 1 :].lstrip()
    if not rest.startswith('"'):
        return None
    out = []
    i = 1
    while i < len(rest):
        c = rest[i]
        if c == "\\":
            if i + 1 < len(rest):
                n = rest[i + 1]
                out.append("\n" if n == "n" else ("\t" if n == "t" else n))
                i += 2
                continue
        if c == '"':
            break
        out.append(c)
        i += 1
    return "".join(out) if out else None


def _strip_thought_block(text: str) -> str:
    """Remove bloco <thought>...</thought> da resposta (reflexão interna, não exibir ao usuário)."""
    if not text or "<thought>" not in text:
        return text
    import re
    return re.sub(r"<thought>[\s\S]*?</thought>\s*", "", text, flags=re.IGNORECASE).strip()


def _strip_json_wrapper(text: str) -> str:
    """Remove wrapper JSON da resposta quando a IA coloca JSON no answer."""
    if not text or not text.strip().startswith("{"):
        return text
    data = _parse_json(text)
    if data and data.get("mode") == "answer":
        return str(data.get("answer") or "").strip()
    extracted = _extract_answer_from_raw(text)
    if extracted:
        return extracted
    return text


def _parse_json(text: str) -> Dict[str, Any] | None:
    """Extrai e parseia um JSON de tools/answer mesmo com markdown ou texto ao redor."""
    if not text:
        return None
    s = text.strip()
    for marker in ("```json", "```"):
        if marker in s:
            i = s.find(marker)
            s = s[i + len(marker) :].strip()
            if s.endswith("```"):
                s = s[: s.rfind("```")].strip()
            break
    start = s.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = None
    escape = False
    end = -1
    for i in range(start, len(s)):
        c = s[i]
        if escape:
            escape = False
            continue
        if c == "\\" and in_string:
            escape = True
            continue
        if in_string:
            if c == in_string:
                in_string = None
            continue
        if c in ('"', "'"):
            in_string = c
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end == -1:
        end = s.rfind("}")
    if end == -1 or end < start:
        return None
    try:
        return json.loads(s[start : end + 1])
    except Exception:
        return None


def _format_tool_reply(tool_name: str, args: Dict, payload: Dict) -> str:
    """Formata o resultado de uma tool para texto amigável (igual ao engine)."""
    if tool_name == "analisar_arquivo":
        return payload.get("text") or "Análise concluída, mas não foi possível obter o texto do relatório."
    if tool_name == "analisar_projeto":
        return payload.get("texto") or "Análise de projeto concluída, mas não foi possível obter o texto formatado."
    if tool_name == "listar_arquivos":
        arquivos = payload.get("arquivos") or []
        if not arquivos:
            return "Não encontrei arquivos para os critérios informados."
        linhas = ["Arquivos encontrados:"] + [f"- {a}" for a in arquivos]
        return "\n".join(linhas)
    if tool_name == "ler_arquivo_texto":
        conteudo = payload.get("conteudo") or ""
        caminho = args.get("caminho") or "arquivo"
        if not conteudo:
            return f"O arquivo {caminho} está vazio ou não pôde ser lido."
        return f"Conteúdo de {caminho} (parcial se muito grande):\n\n{conteudo}"
    if tool_name == "observar_ambiente":
        resumo = payload.get("resumo") or ""
        sugestao = payload.get("sugestao") or ""
        return (resumo + "\n\n" + sugestao) if sugestao else (resumo or "Observei o projeto, mas não consegui gerar um resumo útil.")
    if tool_name == "criar_projeto_arquivos":
        root = payload.get("root") or ""
        files = payload.get("files") or []
        if not payload.get("ok"):
            return f"Não consegui criar o projeto: {payload.get('error') or 'erro desconhecido.'}"
        linhas = ["Projeto criado com sucesso.", f"Pasta raiz: {root or 'generated_projects/'}"]
        if files:
            linhas.append("Arquivos criados:")
            linhas.extend(f"- {p}" for p in files)
        try:
            slug = Path(root).name if root else ""
        except Exception:
            slug = ""
        if slug:
            linhas.append("")
            linhas.append(f"[PREVIEW_URL]: /generated/{slug}/index.html")
        return "\n".join(linhas)
    if tool_name == "criar_zip_projeto":
        if not payload.get("ok"):
            return f"Não consegui preparar o ZIP do projeto: {payload.get('error') or 'erro desconhecido.'}"
        script_path = payload.get("script_path") or ""
        zip_output = payload.get("zip_output") or ""
        command = payload.get("command") or ""
        zip_pending = payload.get("zip_pending") is True
        linhas = [
            "Projeto compactado (gerando em background)." if zip_pending else "Script de compactação criado com sucesso.",
            f"Script: {script_path}",
            f"ZIP de saída: {zip_output or 'definido no script'}",
        ]
        if command and not zip_pending:
            linhas.append(f"Para gerar o ZIP, execute no terminal:\n{command}")
        zip_basename = Path(zip_output).name if zip_output else ""
        if zip_basename and zip_basename.endswith(".zip"):
            linhas.append("")
            linhas.append(f"[DOWNLOAD]:/download/{zip_basename}")
        return "\n".join(linhas)
    if tool_name == "get_current_time":
        if not payload.get("ok"):
            return f"Não foi possível obter o horário: {payload.get('error') or 'erro desconhecido.'}"
        dt = payload.get("datetime_brasilia", "")
        date = payload.get("date", "")
        time = payload.get("time", "")
        return f"Horário atual (Brasília/São Paulo): {dt} — Data: {date}, Hora: {time}"
    if tool_name == "buscar_web":
        if not payload.get("ok"):
            return f"Busca não disponível: {payload.get('error') or 'erro desconhecido.'}"
        resultados = payload.get("resultados") or []
        if not resultados:
            return "__FALLBACK_LLM__"
        linhas = ["Resultados da busca:"] + [
            f"- **{r.get('titulo', '')}**: {r.get('snippet', '')[:200]}..."
            for r in resultados[:5]
        ]
        return "\n".join(linhas)
    if tool_name in ("fs_create_file", "fs_create_folder", "fs_delete_file"):
        if not payload.get("ok"):
            return f"Erro ao executar {payload.get('action', tool_name)}: {payload.get('error') or 'erro desconhecido.'}"
        action = payload.get("action", tool_name)
        path = payload.get("path", "")
        return f"Operação concluída: {action} em {path}"
    if tool_name == "generate_project_map":
        if not payload.get("ok"):
            return f"Erro ao gerar mapa: {payload.get('error') or 'erro desconhecido.'}"
        path = payload.get("path", "")
        stats = payload.get("stats", {})
        return f".yui_map.json gerado em {path}. Arquivos: {stats.get('total_files', 0)}, com dependências: {stats.get('total_with_deps', 0)}"
    if tool_name == "create_mission":
        if not payload.get("ok"):
            return f"Não foi possível criar a missão: {payload.get('error') or 'erro desconhecido.'}"
        m = payload.get("mission") or {}
        proj = m.get("project") or ""
        goal = m.get("goal") or ""
        return f"✨ Missão criada: {proj} — {goal}. Avance uma tarefa por vez e use update_mission_progress ao concluir."
    if tool_name == "update_mission_progress":
        if payload.get("ok"):
            return "Progresso da missão atualizado."
        return f"Não foi possível atualizar: {payload.get('error') or payload.get('message') or 'missão não encontrada.'}"
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _yield_in_chunks(text: str, chunk_size: int = CHUNK_SIZE) -> Generator[str, None, None]:
    """Simula streaming entregando o texto em pedaços."""
    for i in range(0, len(text), chunk_size):
        yield text[i : i + chunk_size]


def _fallback_llm_response(
    client,
    user_message: str,
    msgs: List[Dict[str, str]],
    hint: str,
) -> str:
    """
    Fallback: quando skill/tool falha ou busca retorna vazio, chama LLM para responder.
    Nunca retorna "Nenhum resultado encontrado" — IA sempre tenta ajudar.
    """
    if not client or not user_message:
        return "Posso ajudar de outra forma. Descreva o que precisa."
    fallback_msgs = list(msgs)
    fallback_msgs.append({
        "role": "system",
        "content": hint + " Responda em português, de forma útil e amigável.",
    })
    fallback_msgs.append({"role": "user", "content": user_message})
    try:
        r = client.chat.completions.create(
            model=MODEL,
            messages=fallback_msgs,
            temperature=0.6,
            max_tokens=4096,
        )
        content = ""
        if r.choices and len(r.choices) > 0:
            content = (r.choices[0].message.content or "").strip()
        return content or "Posso ajudar de outra forma. O que você gostaria de saber?"
    except Exception:
        return "Desculpe, não consegui responder no momento. Tente reformular a pergunta."


# ==========================================================
# FUNÇÃO PRINCIPAL DO AGENTE (gerador: yield = chunk para o frontend)
# ==========================================================


HEATHCLIFF_SYSTEM_PROMPT = """Você é o Heathcliff, modo engenheiro da Yui. Inspirado no Composer, focado em SaaS, APIs e arquitetura.

REGRAS OBRIGATÓRIAS:
1. REFLEXÃO PRÉ-RESPOSTA: Para tarefas complexas (código, múltiplos arquivos, refatoração), comece com um bloco <thought> detalhando: lógica da solução, arquivos impactados, dependências e riscos. Exemplo:
   <thought>
   - Objetivo: criar API de login
   - Arquivos: auth.py (novo), routes.py (update), models.py (update)
   - Dependências: bcrypt, jwt
   - Riscos: validar sanitização de inputs
   </thought>
   Depois do </thought>, prossiga com a resposta ou código.
2. ANTES de responder, SEMPRE analise a estrutura de pastas (use listar_arquivos se disponível) para entender o projeto.
3. SEMPRE verifique requirements.txt (Python) ou package.json (Node) antes de sugerir código. NUNCA sugira bibliotecas que não estejam nesses arquivos.
4. Escreva código PRONTO PARA PRODUÇÃO: tratamento de erros, validação de inputs, segurança (sanitização, prepared statements).
5. Utilize o Workspace ao MÁXIMO: proponha arquivos completos, estrutura de pastas clara, convenções consistentes.
6. Prefira soluções escaláveis e bem documentadas.
7. Ao criar projetos, use criar_projeto_arquivos e criar_zip_projeto para gerar o ZIP. Inclua sempre [DOWNLOAD]:/download/nome.zip na resposta final.
8. Use get_current_time() quando precisar de horário real (logs, timestamps, agendamento, saudações).
9. Use buscar_web(query) quando precisar verificar informações externas.
10. Para criar tarefas para o usuário organizar o desenvolvimento, inclua na resposta linhas no formato [TASK]: Nome da tarefa (uma por linha). Ex: [TASK]: Corrigir erro de download no Zeabur.
11. MULTI-WRITE: Para alterar vários arquivos de uma vez, use o formato:
    [CREATE_FILE: caminho/arquivo.py]
    ```python
    conteúdo do arquivo
    ```
    [UPDATE_FILE: caminho/existente.py]
    ```python
    conteúdo atualizado
    ```
    [DELETE_FILE: caminho/obsoleto.py]
    (uma linha por ação, seguida do bloco de código quando aplicável)
12. CONFIRMAÇÃO: Se sua alteração afetar MAIS DE 3 ARQUIVOS, inclua no início da resposta: [REQUIRE_CONFIRM] e liste os arquivos. O usuário verá um checklist antes de aplicar. Ex: [REQUIRE_CONFIRM] Arquivos: a.py, b.py, c.py, d.py
13. Responda em português do Brasil.
"""


def _salvar_memoria_ia_se_relevante(user_id: str, chat_id: str, user_msg: str, reply: str) -> None:
    """Salva resumo em memoria_ia quando for comando importante ou conclusão de código."""
    if not user_id or not reply or len(reply) < 20:
        return
    triggers = ("criar", "implementar", "adicionar", "corrigir", "alterar", "refatorar", "configurar", "crie", "implemente")
    user_lower = (user_msg or "").lower()
    has_trigger = any(t in user_lower for t in triggers)
    has_code = "```" in reply or "[DOWNLOAD]:" in reply or "Projeto criado" in reply
    if not (has_trigger or has_code):
        return
    resumo = (reply[:500] + "..." if len(reply) > 500 else reply).strip()
    tags = []
    if "db" in user_lower or "banco" in user_lower or "sql" in user_lower:
        tags.append("#db")
    if "login" in user_lower or "auth" in user_lower or "autenticação" in user_lower:
        tags.append("#login")
    if "estilo" in user_lower or "css" in user_lower or "ui" in user_lower or "interface" in user_lower:
        tags.append("#estilo")
    if "api" in user_lower or "endpoint" in user_lower:
        tags.append("#api")
    if not tags:
        tags.append("#projeto")
    salvar_memoria_ia(user_id, resumo, ",".join(tags), chat_id)


def _get_mission_context(user_id: str, chat_id: str) -> str:
    """Project Brain: injeta missão ativa no contexto."""
    try:
        from core.project_manager import get_active_mission, mission_to_prompt
        mission = get_active_mission(user_id=user_id, chat_id=chat_id)
        return mission_to_prompt(mission) or ""
    except Exception:
        return ""


def _get_lessons_context() -> str:
    """Lê .yui_lessons.md (memória de erros) para o Heathcliff."""
    try:
        from core.lessons_learner import get_lessons_for_prompt
        return get_lessons_for_prompt() or ""
    except Exception:
        return ""


def _get_dependencies_context() -> str:
    """Lê requirements.txt e package.json do sandbox/projeto para o Heathcliff."""
    try:
        from config import settings

        parts = []
        for base in (Path(settings.SANDBOX_DIR), Path(settings.GENERATED_PROJECTS_DIR), Path(settings.BASE_DIR)):
            if not base.exists():
                continue
            req_path = base / "requirements.txt"
            if req_path.is_file():
                txt = req_path.read_text(encoding="utf-8", errors="replace").strip()
                if txt:
                    parts.append(f"requirements.txt ({base.name}):\n{txt[:1500]}")
            pkg_path = base / "package.json"
            if pkg_path.is_file():
                txt = pkg_path.read_text(encoding="utf-8", errors="replace").strip()
                if txt:
                    parts.append(f"package.json ({base.name}):\n{txt[:1500]}")
        if parts:
            return (
                "DEPENDÊNCIAS DISPONÍVEIS no projeto (use SOMENTE estas bibliotecas):\n\n"
                + "\n\n---\n\n".join(parts[-4:])
            )
    except Exception:
        pass
    return ""


def agent_controller(
    user_id: str,
    chat_id: str,
    user_message: str,
    model: str = "yui",
    confirm_high_cost: bool = False,
    active_files: Optional[list] = None,
    console_errors: Optional[list] = None,
    workspace_open: bool = False,
) -> Generator[str, None, None]:
    """
    Fluxo central da YUI.

    1) Busca memória e contexto
    2) Chama a IA uma vez (resposta em JSON: mode answer ou tools)
    3) Se tools → executa e monta texto da resposta
    4) Entrega a resposta final em chunks (streaming)
    5) Salva memória

    O frontend só recebe texto; nunca JSON cru.
    model: "yui" | "heathcliff" | "auto" (Arbitration Engine decide o líder).
    """
    if not user_id or not isinstance(user_id, str):
        for c in _yield_in_chunks("Erro: user_id inválido."):
            yield c
        return
    if not chat_id or not isinstance(chat_id, str):
        for c in _yield_in_chunks("Erro: chat_id inválido."):
            yield c
        return
    if not user_message or not isinstance(user_message, str):
        for c in _yield_in_chunks("Envie uma mensagem para continuar."):
            yield c
        return

    import time
    turn_start = time.time()
    tools_executed_this_turn: List[str] = []
    files_altered_this_turn: List[str] = []
    errors_detected_this_turn: List[str] = []
    loop_detected_this_turn = False
    tools_ok_this_turn = True

    try:
        # ---------- 0) Energy check: freio cognitivo ----------
        start_energy = 100.0
        if get_energy_manager:
            em = get_energy_manager()
            start_energy = em.energy
            if not em.can_execute():
                for c in _yield_in_chunks("⚠️ A Yui precisa de um momento para recuperar energia. Tente novamente em instantes."):
                    yield c
                return

        # ---------- Agent Context: user_id/chat_id para tools (ex: create_mission) ----------
        try:
            from core.agent_context import set_agent_context
            set_agent_context(user_id, chat_id)
        except Exception:
            pass

        # ---------- Context Engine: memória operacional (workspace, arquivo aberto) ----------
        try:
            from core.context_engine import update_from_snapshot
            update_from_snapshot(user_id, workspace_open=workspace_open, active_files=active_files, chat_id=chat_id)
        except Exception:
            pass

        # ---------- Persona Router: Intent → Context → persona_ativa ----------
        try:
            from core.context_engine import get_context
            from core.reflection_loop import get_estado_reflexao
            from core.persona_router import decidir_persona
            ctx = get_context(user_id, chat_id)
            ctx_dict = ctx.to_dict()
            ctx_dict["estado_reflexao"] = get_estado_reflexao()
            intent = get_action_planner().inferir_intencao(user_message)
            decision = decidir_persona(intent, ctx_dict, user_preference=None)
            ctx.set("persona_ativa", decision.persona)
        except Exception:
            pass

        # ---------- Event Bus: agent_requested (Governor/observers podem reagir) ----------
        try:
            from core.event_bus import emit
            emit("agent_requested", model=model, user_message=user_message)
        except Exception:
            pass

        # ---------- Persona Router + Arbitration: model "auto" → decide quem age ----------
        effective_model = model
        is_hybrid = False
        if model == "auto":
            # Persona Router (intent + context) tem prioridade quando disponível
            try:
                from core.context_engine import get_context
                ctx = get_context(user_id, chat_id)
                persona_ativa = ctx.get("persona_ativa")
                if persona_ativa in ("yui", "heathcliff"):
                    effective_model = persona_ativa
                elif decide_leader:
                    arb = decide_leader(
                        user_message,
                        user_preference=None,
                        active_files=active_files,
                        has_console_errors=bool(console_errors),
                    )
                    effective_model = arb.leader if arb.leader != "hybrid" else "heathcliff"
                    is_hybrid = arb.leader == "hybrid"
            except Exception:
                if decide_leader:
                    arb = decide_leader(
                        user_message,
                        user_preference=None,
                        active_files=active_files,
                        has_console_errors=bool(console_errors),
                    )
                    effective_model = arb.leader if arb.leader != "hybrid" else "heathcliff"
                    is_hybrid = arb.leader == "hybrid"

        # ---------- 1) Context Engine: histórico + contexto do projeto + memórias + Context Kernel ----------
        context_snapshot = {
            "active_files": active_files or [],
            "console_errors": console_errors or [],
        }
        ctx = montar_contexto_ia(
            user_id, chat_id, user_message,
            raiz_projeto=".",
            max_mensagens=MAX_HISTORY,
            context_snapshot=context_snapshot,
        )

        # ---------- World Model: mapa do ambiente ----------
        if get_world_model:
            try:
                wm = get_world_model()
                wm.update_from_scan(".")
                wm.sync_from_modules()
            except Exception:
                pass

        # ---------- 0.5) Meta-Cognition: observador interno (antes de planner) ----------
        context_size = sum(1 for k in ("historico", "contexto_projeto", "memoria_vetorial", "contexto_chat_anterior", "memoria_eventos") if ctx.get(k))
        meta_signals = {}
        if get_metacognition and _build_state:
            state = _build_state(context_size=context_size)
            meta_signals = get_metacognition().analyze(state)
            if meta_signals.get("loop_detected"):
                for c in _yield_in_chunks("⚠️ Detectei repetição nas ações. Simplificando a resposta."):
                    yield c
                return

        # ---------- Cognitive Budget: tokens, tempo, memória, profundidade ----------
        server_load_high = bool(should_use_fast_mode and should_use_fast_mode())
        depth = "normal"
        budget = None
        if reset_budget_for_turn and get_cognitive_budget:
            budget = reset_budget_for_turn()
            em = get_energy_manager() if get_energy_manager else None
            depth = budget.recommend_depth(
                user_message=user_message,
                energy=em.energy if em else None,
                context_size=context_size,
                meta_signals=meta_signals,
                server_load_high=server_load_high,
            )

        # ---------- Strategy Engine: escolhe como pensar ----------
        strategy = "exploration"
        if get_strategy_engine:
            em = get_energy_manager() if get_energy_manager else None
            goal_prio = 0.0
            try:
                goals_pre = get_active_goals(user_id, chat_id, energy=em.energy if em else None) if is_enabled("goals") else []
                goal_prio = goals_pre[0].priority if goals_pre else 0.0
            except Exception:
                pass
            strategy = get_strategy_engine().choose(
                meta_signals=meta_signals,
                energy=em.energy if em else None,
                goal_priority=goal_prio,
                has_error=bool(meta_signals.get("last_failed")),
            )

        if filter_context_blocks:
            if budget:
                top = budget.get_max_context_items(depth)
            elif get_strategy_engine:
                top = get_strategy_engine().get_attention_top(strategy)
            else:
                top = 2 if (meta_signals.get("context_overload") or meta_signals.get("simplified_mode")) else None
            ctx = filter_context_blocks(ctx, user_message=user_message, top=top)
        msgs: List[Dict[str, str]] = list(ctx.get("historico") or [])

        # Context Builder: data/hora e regras base (antes de tudo)
        try:
            from yui_ai.core.context_builder import contexto_base_sistema
            ctx_base = contexto_base_sistema()
            if ctx_base:
                msgs.insert(0, {"role": "system", "content": ctx_base})
        except Exception:
            pass

        if ctx.get("context_kernel"):
            msgs.insert(0, {
                "role": "system",
                "content": (
                    "Contexto em tempo real (arquivos ativos, erros do console, workspace):\n\n"
                    + ctx["context_kernel"]
                )
            })
        if ctx.get("contexto_projeto"):
            msgs.insert(0, {
                "role": "system",
                "content": (
                    "Você é a YUI, uma IA desenvolvedora. Use o contexto do projeto abaixo para responder "
                    "de forma compatível com o código existente.\n\n" + ctx["contexto_projeto"]
                )
            })
        if ctx.get("memoria_vetorial"):
            msgs.insert(0, {
                "role": "system",
                "content": (
                    "Você é a YUI, uma IA desenvolvedora especialista. Use o contexto recuperado da memória do projeto:\n"
                    + ctx["memoria_vetorial"]
                )
            })
        if ctx.get("session_context"):
            msgs.insert(0, {
                "role": "system",
                "content": ctx["session_context"],
            })
        if ctx.get("operational_context"):
            msgs.insert(0, {
                "role": "system",
                "content": ctx["operational_context"],
            })
        if ctx.get("contexto_chat_anterior"):
            msgs.insert(0, {
                "role": "system",
                "content": f"Contexto anterior relevante gerado pela própria Yui:\n\n{ctx['contexto_chat_anterior']}",
            })
        if ctx.get("memoria_eventos"):
            msgs.insert(0, {"role": "system", "content": ctx["memoria_eventos"]})
        if ctx.get("memoria_ia"):
            msgs.insert(0, {
                "role": "system",
                "content": "Use as decisões abaixo (memória de longo prazo) para manter consistência:\n\n" + ctx["memoria_ia"],
            })
        if ctx.get("system_state"):
            msgs.insert(0, {"role": "system", "content": f"Estado da Yui: {ctx['system_state']}"})

        # ---------- Project Brain: missão ativa (antes do planner) ----------
        mission_context = _get_mission_context(user_id, chat_id)
        if mission_context:
            msgs.insert(0, {"role": "system", "content": mission_context})

        # ---------- Action Engine: sugestão de tool (roteamento de intenção) ----------
        intent = None
        try:
            from core.self_state import get as get_self_state
            last_tool = (get_self_state("last_action") or "").replace("tool:", "")
            from core.engine import route_action
            intent = route_action(
                user_message,
                last_tool=last_tool or None,
                active_files=active_files,
                has_console_errors=bool(console_errors),
            )
            if intent.tool_hint and intent.confidence > 0.3:
                msgs.insert(0, {
                    "role": "system",
                    "content": f"[Action Engine] Sugestão: considere usar a ferramenta '{intent.tool_hint}' para esta tarefa (confiança {intent.confidence:.0%}).",
                })
        except Exception:
            pass

        # ---------- Capability Router: antes do planner ----------
        route_decision = None
        intention = None
        try:
            intention = infer_intention(user_message)
            from core.capability_router import route, get_routing_display
            route_decision = route(
                user_message,
                intention=intention,
                action=intent.action if intent else None,
                tool_hint=intent.tool_hint if intent else None,
            )
            from core.observability import record_activity
            record_activity("routing", get_routing_display(route_decision))
        except Exception:
            pass

        profile = ctx.get("user_profile") or get_user_profile(user_id)
        if profile:
            nivel = profile.get("nivel_tecnico") or "desconhecido"
            langs = profile.get("linguagens_pref") or ""
            modo = profile.get("modo_resposta") or "dev"
            perfil_txt = (
                f"Usuário: nível {nivel}, linguagens {langs or 'não especificado'}, modo {modo}. "
                "Ajuste o tom da resposta."
            )
            msgs.insert(0, {"role": "system", "content": perfil_txt})

        skills_system = _build_skills_system()
        msgs.insert(0, {"role": "system", "content": _build_tool_system(user_message) + skills_system})
        if effective_model == "heathcliff":
            msgs.insert(0, {"role": "system", "content": HEATHCLIFF_SYSTEM_PROMPT})
            if is_hybrid and get_hybrid_modifier:
                msgs.insert(0, {"role": "system", "content": get_hybrid_modifier()})
            deps = _get_dependencies_context()
            if deps:
                msgs.insert(0, {"role": "system", "content": deps})
            lessons = _get_lessons_context()
            if lessons:
                msgs.insert(0, {"role": "system", "content": lessons})
            if get_system_state_for_prompt:
                telemetry = get_system_state_for_prompt(always_include=True)
                if telemetry:
                    msgs.insert(-1, {"role": "system", "content": telemetry})
        # Autopercepção: avisa a Yui sobre carga do servidor (modo economia)
        elif get_system_state_for_prompt:
            autopercepcao = get_system_state_for_prompt()
            if autopercepcao:
                msgs.insert(-1, {"role": "system", "content": autopercepcao})
        msgs.append({"role": "user", "content": user_message})

        # ---------- Planner Core (v2): planeja antes de responder ----------
        transition(AgentState.PLANNING)
        yield "__STATUS__:planejando"
        if get_energy_manager:
            get_energy_manager().consume(COST_PLANNER)
        goals_ativos = []
        if is_enabled("goals"):
            try:
                em = get_energy_manager() if get_energy_manager else None
                goals_ativos = get_active_goals(user_id, chat_id, energy=em.energy if em else None)
            except Exception:
                pass
        if is_enabled("planner"):
            try:
                from core.resource_governor import allow_planner
                planner_ok = allow_planner().allow
            except Exception:
                planner_ok = True
            if planner_ok:
                try:
                    plano_execucao = criar_plano(user_message)
                    if plano_execucao and plano_execucao.strip():
                        msgs.insert(0, {"role": "system", "content": plano_execucao.strip()})
                    # intention já obtido pelo Capability Router
                    if intention is None:
                        intention = infer_intention(user_message)
                    task_graph = build_task_graph(intention, user_message)
                    plan_steps = get_planned_steps_for_prompt(task_graph)
                    if plan_steps:
                        msgs.insert(0, {"role": "system", "content": plan_steps})
                    # Planner estruturado (memory aware, tool reasoning, goals aware, meta-aware, strategy-aware, budget-aware)
                    max_steps = LIMIT_MAX_STEPS
                    if budget:
                        max_steps = min(max_steps, budget.get_max_plan_steps(depth))
                    if get_strategy_engine:
                        max_steps = min(max_steps, get_strategy_engine().get_max_steps(strategy))
                    if meta_signals.get("simplified_mode") or meta_signals.get("too_many_steps"):
                        max_steps = min(max_steps, 2)
                    # Capability Router: skip_planner reduz planner pesado
                    if route_decision and route_decision.skip_planner:
                        max_steps = min(max_steps, 2)
                    plan = criar_plano_estruturado(user_message, user_id, chat_id, max_steps=max_steps, goals_ativos=goals_ativos or None)
                    if plan:
                        plan_txt = plan_to_prompt(plan, goals_ativos or None)
                        if get_world_model:
                            hint = get_world_model().get_focus_hint()
                            if hint:
                                plan_txt = f"[World Model] {hint}\n\n{plan_txt}"
                        msgs.insert(0, {"role": "system", "content": plan_txt})
                except Exception:
                    pass

        if not client:
            for c in _yield_in_chunks("⚠️ Configure OPENAI_API_KEY no servidor para respostas da Yui."):
                yield c
            return

        # ---------- 1.5) Alerta de orçamento: estimar custo antes de chamar ----------
        prompt_chars = sum(len(str(m.get("content", ""))) for m in msgs)
        estimated_cost = estimate_cost_brl(prompt_chars)
        if estimated_cost > BUDGET_ALERT_BRL and not confirm_high_cost:
            msg = f"⚠️ Esta tarefa pode custar aproximadamente R$ {estimated_cost:.2f}. Deseja continuar? (Responda 'sim' para prosseguir)"
            yield f"__BUDGET_CONFIRM__:{estimated_cost:.2f}:{msg}"
            return

        # ---------- 2) Uma chamada à IA (resposta estruturada) ----------
        if get_energy_manager:
            get_energy_manager().consume(COST_RESPONDER_IA)
        em = get_energy_manager() if get_energy_manager else None
        energy = em.energy if em else None
        if get_identity_core:
            identity = get_identity_core()
            identity.apply_energy_context(energy)
            depth = identity.get_effective_response_depth(energy)
            if depth == "short" or meta_signals.get("simplified_mode"):
                msgs.insert(-1, {"role": "system", "content": "Responda de forma resumida (máx 2-3 frases)."})
        elif get_energy_manager and get_energy_manager().is_critical():
            msgs.insert(-1, {"role": "system", "content": "Energia baixa: responda de forma MUITO resumida (máx 2-3 frases)."})
        transition(AgentState.EXECUTING)
        response = client.chat.completions.create(
            model=MODEL,
            messages=msgs,
            temperature=0.6,
            max_tokens=8192,
        )
        raw_content = ""
        if response.choices and len(response.choices) > 0:
            raw_content = (response.choices[0].message.content or "").strip()
        prompt_tokens, completion_tokens = 0, 0
        try:
            usage = getattr(response, "usage", None)
            if usage:
                prompt_tokens = getattr(usage, "prompt_tokens") or 0
                completion_tokens = getattr(usage, "completion_tokens") or 0
                if prompt_tokens or completion_tokens:
                    record_response_cost(prompt_tokens, completion_tokens)
        except Exception:
            pass
        data = _parse_json(raw_content)
        if data is None and ("mode" in raw_content and ("tools" in raw_content or "tool" in raw_content)):
            data = _parse_json(raw_content[raw_content.find("{"):] if "{" in raw_content else raw_content)
        if data is None and "usar_skill" in (raw_content or ""):
            data = _parse_json(raw_content[raw_content.find("{"):] if "{" in raw_content else raw_content)

        # ---------- 3a) Se for skill → executar e usar resultado como resposta ----------
        reply = ""
        if isinstance(data, dict) and data.get("usar_skill") and is_enabled("skills"):
            if get_energy_manager:
                get_energy_manager().consume(COST_TOOL)
            nome_skill = str(data.get("usar_skill") or "").strip()
            dados_skill = data.get("dados") if isinstance(data.get("dados"), dict) else {}
            sucesso, resultado = executar_skill(nome_skill, dados_skill)
            tools_executed_this_turn.append(f"skill:{nome_skill}")
            tools_ok_this_turn = sucesso
            if not sucesso:
                errors_detected_this_turn.append(str(resultado))
            set_last_action(f"skill:{nome_skill}")
            if sucesso:
                reply = json.dumps(resultado, ensure_ascii=False, indent=2) if isinstance(resultado, dict) else str(resultado)
            else:
                set_last_error(f"Não foi possível executar a skill '{nome_skill}': {resultado}")
                if client:
                    reply = _fallback_llm_response(
                        client, user_message, msgs,
                        f"A skill '{nome_skill}' falhou: {resultado}. Responda ao usuário de forma útil com suas capacidades.",
                    )
                else:
                    reply = "Não consegui executar essa ação. Posso ajudar de outra forma?"

        # ---------- 3b) Se for tool → executar e montar resposta (só se capability tools ativa) ----------
        elif isinstance(data, dict) and data.get("mode") in ("tool", "tools") and is_enabled("tools"):
            planner = get_action_planner()
            steps: List[Dict] = []
            if data.get("mode") == "tool":
                steps = [{"tool": str(data.get("tool") or "").strip(), "args": data.get("args") or {}}]
            else:
                for s in data.get("steps") or []:
                    if isinstance(s, dict) and s.get("tool"):
                        steps.append({"tool": str(s["tool"]).strip(), "args": s.get("args") or {}})

            partes: List[str] = []
            last_step_ok = True  # para goal update
            for i, step in enumerate(steps):
                if i >= LIMIT_MAX_STEPS:
                    break
                if get_metacognition and get_metacognition().analyze(steps_executed=i).get("loop_detected"):
                    loop_detected_this_turn = True
                    partes.append("Detectei repetição. Interrompendo execução.")
                    break
                if get_energy_manager and not get_energy_manager().can_execute():
                    partes.append("Energia esgotada. Interrompendo execução.")
                    break
                if get_energy_manager:
                    get_energy_manager().consume(COST_TOOL)
                tool_name = step["tool"]
                args = step.get("args") or {}
                if get_metacognition and tool_name == "criar_projeto_arquivos":
                    redundant, motivo = get_metacognition().check_redundant_action(tool_name, args)
                    if redundant:
                        partes.append(f"⚠️ {motivo} Pulando criação duplicada.")
                        continue
                label = planner.get_label_for_tool(tool_name)
                yield f"__STATUS__:executing_tools:{label}"
                try:
                    from core.context_engine import get_context
                    get_context(user_id, chat_id).set("task_ativa", tool_name)
                except Exception:
                    pass
                result = get_task_engine().executar_tool(tool_name, args)
                emit("tool_executed", tool_name=tool_name, args=args, result=result)
                tools_executed_this_turn.append(tool_name)
                if not result.get("ok"):
                    last_step_ok = False
                    tools_ok_this_turn = False
                    err = result.get("error") or "erro desconhecido."
                    errors_detected_this_turn.append(err)
                    set_last_error(err)
                    partes.append(f"Não consegui executar '{tool_name}': {err}")
                    try:
                        from core.context_engine import get_context
                        get_context(user_id, chat_id).set("ultimo_erro", err)
                    except Exception:
                        pass
                    # Reflexão: decidir se continua ou para
                    from core.planner import PlanStep
                    refl = refletir({"ok": False, "error": err}, PlanStep(goal="", action="", tool=tool_name))
                    if refl.get("ajustar") and refl.get("motivo"):
                        partes.append(f"(Ajuste: {refl['motivo']})")
                    continue
                last_step_ok = True
                set_last_action(f"tool:{tool_name}")
                payload = result.get("result") or {}
                if tool_name in ("fs_create_file", "fs_create_folder", "criar_projeto_arquivos"):
                    path = args.get("path") or payload.get("path")
                    if path:
                        files_altered_this_turn.append(str(path))
                    for p in payload.get("files") or []:
                        files_altered_this_turn.append(p if isinstance(p, str) else str(p.get("path", p)))
                if get_world_model and tool_name == "criar_projeto_arquivos" and payload.get("ok"):
                    try:
                        wm = get_world_model()
                        known = list(wm.project.get("known_files", []))
                        for p in payload.get("files") or []:
                            path = p if isinstance(p, str) else str(p)
                            if path and path not in known:
                                known.append(path)
                        wm.project["known_files"] = known[-50:]
                    except Exception:
                        pass
                msg = _format_tool_reply(tool_name, args, payload)
                if msg == "__FALLBACK_LLM__":
                    if client:
                        query = args.get("query") or user_message
                        fallback_reply = _fallback_llm_response(
                            client, user_message, msgs,
                            f"A busca na web não retornou resultados para: {query}. Responda com seu conhecimento geral.",
                        )
                        partes.append(fallback_reply)
                    else:
                        partes.append("A busca não retornou resultados. Posso ajudar de outra forma?")
                else:
                    partes.append(msg)
                # Ao criar projeto, gera ZIP e adiciona link de download clicável (se ainda não tiver)
                if tool_name == "criar_projeto_arquivos" and payload.get("ok") and "[DOWNLOAD]:" not in msg:
                    root_dir = payload.get("root") or args.get("root_dir") or ""
                    if root_dir:
                        slug = Path(root_dir).name if root_dir else ""
                        zip_result = {}
                        if get_energy_manager:
                            try:
                                get_energy_manager().consume(COST_TOOL)
                            except Exception:
                                pass
                        try:
                            zip_result = get_task_engine().executar_tool(
                                "criar_zip_projeto",
                                {"root_dir": root_dir, "zip_name": slug or None, "background": True},
                            )
                        except Exception:
                            zip_result = {}
                        if zip_result.get("ok"):
                            zpayload = zip_result.get("result") or {}
                            zip_output = zpayload.get("zip_output") or ""
                            zip_basename = Path(zip_output).name if zip_output else ""
                            if zip_basename and zip_basename.endswith(".zip"):
                                partes.append(f"Projeto compactado. [DOWNLOAD]:/download/{zip_basename}")
                        else:
                            partes.append("Projeto criado, mas não consegui compactar automaticamente agora.")

            final_answer = str(data.get("final_answer") or "").strip()
            if final_answer:
                partes.append("")
                partes.append(final_answer)
            reply = "\n\n".join(p for p in partes if p) if partes else "Execução das ferramentas concluída."
            # Goal update: micro reflexão após execução de tools
            if goals_ativos and is_enabled("goals"):
                try:
                    update_progress(goals_ativos[0].name, last_step_ok)
                except Exception:
                    pass

        elif isinstance(data, dict) and data.get("mode") in ("tool", "tools") and not is_enabled("tools"):
            set_last_action("answer")
            reply = "Ferramentas estão desativadas no momento. Tente descrever o que precisa em texto."

        elif isinstance(data, dict) and data.get("mode") == "answer":
            set_last_action("answer")
            reply = str(data.get("answer") or "").strip() or _strip_thought_block(raw_content.strip())

        else:
            # Evita mostrar JSON bruto: se parece resposta de tools, tenta processar
            raw_clean = _strip_thought_block(raw_content.strip()) if raw_content else ""
            if raw_content and "mode" in raw_content and ("steps" in raw_content or '"tool"' in raw_content):
                reply = processar_resposta_ai(raw_clean)
                if not reply or reply == raw_clean:
                    reply = "Projeto criado."
                    try:
                        from core.pending_downloads import get_recent
                        urls = get_recent()
                        if urls:
                            reply += f" [DOWNLOAD]:{urls[-1]}"
                        else:
                            reply += " Se quiser o arquivo, peça para compactar novamente."
                    except Exception:
                        reply += " Se quiser o arquivo, peça para compactar novamente."
            else:
                reply = _strip_json_wrapper(raw_clean)

        # Normaliza link de download: sandbox://xxx.zip -> /download/xxx.zip
        if reply and "sandbox://" in reply:
            reply = re.sub(r"sandbox://([^\s\)\]]+)", r"/download/\1", reply)

        # ---------- 3c) Reflexão + Middleware: Self-Reflect + Auto Debug ----------
        transition(AgentState.REFLECTING)
        allow_reflection = not budget or budget.get_allow_reflection(depth)
        if client and reply:
            if get_energy_manager and allow_reflection:
                get_energy_manager().consume(COST_REFLECT)
            try:
                def _call_model_reflect(messages):
                    r = client.chat.completions.create(
                        model=MODEL,
                        messages=messages,
                        temperature=0.5,
                        max_tokens=4096,
                    )
                    if r.choices and len(r.choices) > 0:
                        return (r.choices[0].message.content or "").strip()
                    return ""

                if is_enabled("self_reflection") and allow_reflection:
                    melhorou, nova_resposta = avaliar_resposta(_call_model_reflect, msgs, reply)
                    if melhorou and nova_resposta:
                        reply = nova_resposta
                        set_confidence(0.9)

                if is_enabled("auto_debug") and allow_reflection:
                    corrigiu, resposta_debugada = auto_debug(_call_model_reflect, reply)
                    if corrigiu and resposta_debugada:
                        reply = resposta_debugada
                        set_last_action("auto_debug")
            except Exception as e:
                set_last_error(str(e))

        # ---------- 4) Responder ----------
        transition(AgentState.RESPONDING)
        reply = _strip_thought_block(reply)
        reply = processar_resposta_ai(reply)
        reply = _strip_json_wrapper(reply)  # garante que nunca mostre JSON bruto

        # ---------- 4b) Salva resposta na memória contextual do chat ----------
        try:
            salvar_memoria_chat(chat_id, reply)
        except Exception:
            pass

        emit("response_generated", reply=reply, user_message=user_message)

        # ---------- 4c) Cognitive Loop: Observer → Self-Critic → Memory Update ----------
        try:
            from core.cognitive import observe_turn, criticize
            from core.self_state import get as get_self_state
            mode = "tool" if tools_executed_this_turn else ("tools" if len(tools_executed_this_turn) > 1 else "answer")
            obs = observe_turn(
                turn_start=turn_start,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                tools_executed=tools_executed_this_turn,
                files_altered=files_altered_this_turn,
                errors_detected=errors_detected_this_turn,
                reply_length=len(reply),
                mode=mode,
            )
            critique = criticize(
                obs=obs,
                last_action=get_self_state("last_action") or "",
                last_error=get_self_state("last_error") or "",
                loop_detected=loop_detected_this_turn,
                tools_ok=tools_ok_this_turn,
            )
            if critique.efficient:
                set_confidence(min(1.0, 0.5 + critique.score * 0.15))
            else:
                set_confidence(max(0.2, 0.5 + critique.score * 0.1))
        except Exception:
            pass

        # ---------- 5) Entregar resposta em chunks (streaming) ----------
        for chunk in _yield_in_chunks(reply):
            yield chunk

        # ---------- 6) Salvar memória ----------
        save_message(chat_id, "user", user_message, user_id)
        save_message(chat_id, "assistant", reply, user_id)
        # Session Manager: atualiza pensamento atual (RAM)
        try:
            from core.session_manager import append_turn
            append_turn(user_id, user_message, reply, chat_id)
        except Exception:
            pass
        add_event(user_id=user_id, chat_id=chat_id, tipo="curta", conteudo=user_message)
        add_event(user_id=user_id, chat_id=chat_id, tipo="curta", conteudo=reply)
        # Salvar em memoria_ia quando for comando importante ou código finalizado
        try:
            _salvar_memoria_ia_se_relevante(user_id, chat_id, user_message, reply)
        except Exception:
            pass
        emit("memory_saved", chat_id=chat_id, user_id=user_id)
        if get_energy_manager:
            em_final = get_energy_manager()
            consumed = max(0, start_energy - em_final.energy)
            try:
                from core.usage_tracker import record_consumption
                record_consumption(consumed)
            except Exception:
                pass
            em_final.recover()
        if get_strategy_engine:
            try:
                get_strategy_engine().record_result(strategy, success=True)
            except Exception:
                pass
        if get_world_model:
            try:
                get_world_model().sync_from_modules()
                get_world_model().runtime["last_strategy"] = strategy
                get_world_model().save()
            except Exception:
                pass
        transition(AgentState.IDLE)

    except Exception as e:
        transition(AgentState.IDLE)
        erro = f"Erro no Agent Controller: {str(e)}"
        set_last_error(erro)
        if get_strategy_engine:
            try:
                get_strategy_engine().record_result("exploration", success=False)
            except Exception:
                pass
        if get_identity_core:
            err_lower = str(e).lower()
            if "token" in err_lower or "length" in err_lower or "context" in err_lower:
                get_identity_core().learn_from_error("response_too_long", {"error": str(e)})
        print(erro)
        for c in _yield_in_chunks("⚠️ Algo deu errado ao processar sua mensagem."):
            yield c
