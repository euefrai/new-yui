"""
chat_summarizer: gera resumos periódicos de conversas
e grava em memória longa via MemoryManager.
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.memory_manager import add_fact, add_summary


def _format_transcript(messages: List[Dict[str, Any]]) -> str:
    """Monta um texto compacto com os últimos turnos da conversa."""
    linhas: List[str] = []
    for m in messages:
        role = (m.get("role") or "").lower()
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            prefix = "Usuário"
        elif role == "assistant":
            prefix = "Yui"
        else:
            prefix = role.capitalize() or "Outro"
        linhas.append(f"{prefix}: {content}")
    return "\n".join(linhas)


def summarize_chat(user_id: str, chat_id: str, messages: List[Dict[str, Any]]) -> None:
    """
    Usa o motor principal da Yui para gerar um resumo da conversa
    e grava em memória longa (events tipo 'longa').
    """
    # Evita chamadas desnecessárias
    if not messages:
        return

    # Import lazy para evitar ciclos de import
    try:
        from yui_ai.main import processar_texto_web
    except Exception:
        # Se por algum motivo o motor não estiver disponível, falha silenciosa
        return

    transcript = _format_transcript(messages)
    if not transcript:
        return

    prompt = (
        "Você é a Yui, uma IA assistente. Receberá abaixo um trecho recente de uma conversa "
        "entre o usuário e a Yui.\n\n"
        "Tarefa:\n"
        "1) Produza um RESUMO curto em português, focado em:\n"
        "- objetivos do usuário\n"
        "- decisões já tomadas\n"
        "- contexto técnico relevante (linguagens, frameworks, projeto atual)\n"
        "2) Não repita o diálogo literalmente, apenas sintetize o que é importante lembrar.\n"
        "3) Responda em um único parágrafo ou em 3-6 bullets curtos.\n\n"
        "Trecho da conversa:\n"
        "--------------------\n"
        f"{transcript}\n"
        "--------------------\n\n"
        "Agora gere apenas o resumo, sem explicações adicionais."
    )

    try:
        resposta, _msg_id, api_key_missing = processar_texto_web(prompt, reply_to_id=None)
    except Exception:
        # Não deixa erros de LLM quebrarem o fluxo principal do chat
        return

    if api_key_missing:
        return

    summary = (resposta or "").strip()
    if not summary:
        return

    # Grava resumo como memória longa ligada a este chat
    try:
        add_summary(user_id=user_id, chat_id=chat_id, conteudo=summary)
    except Exception:
        # Memória não é crítica para a experiência imediata do usuário
        pass

    # Tenta extrair fatos objetivos de longo prazo a partir do resumo
    try:
        facts_prompt = (
            "A seguir está um RESUMO de uma conversa entre o usuário e a Yui.\n\n"
            "Resumo:\n"
            "--------------------\n"
            f"{summary}\n"
            "--------------------\n\n"
            "Tarefa:\n"
            "- Extraia de 1 a 8 FATOS objetivos e atemporais que sejam úteis para lembrar depois.\n"
            "- Foque em coisas como: objetivos do usuário, preferências, decisões tomadas,\n"
            "  tecnologias/frameworks que ele está usando, características importantes do projeto.\n"
            "- Ignore detalhes muito específicos de uma única mensagem.\n"
            "- Responda APENAS com uma lista em que cada linha começa com '- ' seguida do fato.\n"
            "- Não inclua explicações adicionais nem texto antes/depois da lista."
        )

        facts_text, _msg_id2, api_key_missing2 = processar_texto_web(
            facts_prompt, reply_to_id=None
        )
        if api_key_missing2:
            return

        if not facts_text:
            return

        for raw_line in str(facts_text).splitlines():
            line = raw_line.strip()
            if not line.startswith("-"):
                continue
            # Remove o prefixo '-' ou '- '
            fact = line.lstrip("-").strip()
            if not fact:
                continue
            # Grava como fato de longo prazo (sem chat_id)
            try:
                add_fact(user_id=user_id, conteudo=fact)
            except Exception:
                # Erros individuais não devem quebrar o fluxo
                continue
    except Exception:
        # Extração de fatos é "best effort"
        return

