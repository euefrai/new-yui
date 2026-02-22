# ==========================================================
# YUI CONTEXT ENGINE
# Motor central de contexto: escolhe o que enviar à IA.
# Camadas: short_term_context, long_term_memory, system_state, user_profile.
# contexto = short + memory + system_state
# ==========================================================

from typing import Any, Dict, List, Optional

from core.memory import get_messages
from core.memory_manager import build_context_text
from core.self_state import to_prompt_snippet as self_state_snippet
from core.user_profile import get_user_profile

from backend.ai.context_builder import montar_contexto_projeto
from backend.ai.context_memory import buscar_contexto as buscar_contexto_chat
from backend.ai.vector_memory import buscar_contexto as buscar_contexto_vetorial
from core.memoria_ia import buscar_memoria as buscar_memoria_ia

# Limites para contexto rico (nível ChatGPT)
MAX_MENSAGENS_HISTORICO = 50
MAX_MENSAGENS_DB = 100  # limite na query Supabase
LIMITE_CURTA = 12
LIMITE_LONGA = 12
VETORIAL_LIMITE = 12


def _build_short_term(historico: List[Dict[str, Any]], ultimas: int = 6) -> str:
    """Camada de contexto de curto prazo (últimas mensagens em texto)."""
    if not historico:
        return ""
    window = historico[-ultimas:] if len(historico) > ultimas else historico
    parts = [f"[{m.get('role', 'user')}]: {(m.get('content') or '')[:500]}" for m in window]
    return "\n".join(parts)


def _build_long_term(vetorial: str, eventos: str) -> str:
    """Camada de memória de longo prazo (vetorial + eventos)."""
    combined = (vetorial + "\n\n" + eventos).strip()
    return combined or ""


def _build_system_state() -> str:
    """Estado interno da Yui (última ação, erro, confiança, modo)."""
    try:
        return self_state_snippet()
    except Exception:
        return ""


def montar_contexto_ia(
    user_id: str,
    chat_id: str,
    user_message: str,
    raiz_projeto: str = ".",
    max_mensagens: int = MAX_MENSAGENS_HISTORICO,
    limite_vetorial: int = VETORIAL_LIMITE,
    context_snapshot: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Monta todo o contexto que a IA precisa (contexto inteligente em camadas).

    Retorna:
        historico, contexto_projeto, memoria_vetorial, contexto_chat_anterior, memoria_eventos
        short_term_context: str — resumo/últimas trocas (janela curta)
        long_term_memory: str — memória vetorial + eventos (longo prazo)
        system_state: str — estado interno da Yui (self_state)
        user_profile: dict — perfil do usuário (nível, linguagens, modo)
    """
    out: Dict[str, Any] = {
        "historico": [],
        "contexto_projeto": "",
        "memoria_vetorial": "",
        "memoria_ia": "",
        "contexto_chat_anterior": "",
        "memoria_eventos": "",
        "context_kernel": "",
        "short_term_context": "",
        "long_term_memory": "",
        "system_state": "",
        "session_context": "",
        "operational_context": "",
        "user_profile": {},
    }

    # Histórico do chat (limitado na query — evita RAM infinita)
    raw = get_messages(chat_id, user_id, limit=MAX_MENSAGENS_DB) or []
    if raw:
        window = raw[-max_mensagens:]
        out["historico"] = [
            {"role": m.get("role", "user"), "content": (m.get("content") or "")}
            for m in window
        ]
        out["short_term_context"] = _build_short_term(out["historico"])

    # Contexto do projeto (arquivos)
    try:
        out["contexto_projeto"] = montar_contexto_projeto(raiz_projeto) or ""
    except Exception:
        out["contexto_projeto"] = ""

    # Memória vetorial (trechos relevantes à pergunta)
    try:
        out["memoria_vetorial"] = buscar_contexto_vetorial(user_message, limite=limite_vetorial) or ""
    except Exception:
        out["memoria_vetorial"] = ""

    # Memória de longo prazo (RAG): decisões anteriores do projeto
    try:
        out["memoria_ia"] = buscar_memoria_ia(user_id, query=user_message, chat_id=chat_id, limite=6) or ""
    except Exception:
        out["memoria_ia"] = ""

    # Contexto de respostas anteriores deste chat (RAM)
    try:
        out["contexto_chat_anterior"] = buscar_contexto_chat(chat_id, user_message) or ""
    except Exception:
        out["contexto_chat_anterior"] = ""

    # Memória de eventos (curta + longa)
    try:
        out["memoria_eventos"] = build_context_text(
            user_id=user_id,
            chat_id=chat_id,
            limit_short=LIMITE_CURTA,
            limit_long=LIMITE_LONGA,
        ) or ""
    except Exception:
        out["memoria_eventos"] = ""

    out["long_term_memory"] = _build_long_term(
        (out["memoria_vetorial"] + "\n\n" + out["memoria_ia"]).strip(),
        out["memoria_eventos"],
    )
    out["system_state"] = _build_system_state()

    # Session Manager: pensamento atual (RAM, não DB)
    try:
        from core.session_manager import get_contexto as get_session_contexto
        out["session_context"] = get_session_contexto(user_id, chat_id) or ""
    except Exception:
        out["session_context"] = ""

    # Context Engine: memória operacional (modo, arquivo_aberto, workspace_open)
    try:
        from core.context_engine import get_context
        out["operational_context"] = get_context(user_id, chat_id).to_prompt_snippet() or ""
    except Exception:
        out["operational_context"] = ""

    # Context Kernel: snapshot unificado (arquivos ativos, erros do console)
    if context_snapshot:
        try:
            from core.engine import get_context_snapshot, snapshot_to_prompt
            snapshot = get_context_snapshot(
                user_id=user_id,
                chat_id=chat_id,
                active_files=context_snapshot.get("active_files"),
                console_errors=context_snapshot.get("console_errors"),
                last_stdout=context_snapshot.get("last_stdout", ""),
                last_stderr=context_snapshot.get("last_stderr", ""),
            )
            out["context_kernel"] = snapshot_to_prompt(snapshot)
        except Exception:
            out["context_kernel"] = ""

    # user_profile: nível técnico, linguagens, modo de resposta
    try:
        out["user_profile"] = get_user_profile(user_id) or {}
    except Exception:
        out["user_profile"] = {}

    return out
