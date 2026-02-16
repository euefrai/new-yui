"""
Context Builder — Monta o pacote mental antes de chamar o modelo.
Data/hora, regras e histórico leve → menos tokens, respostas mais coerentes.
"""

from datetime import datetime

try:
    import pytz
except ImportError:
    pytz = None


def _formatar_historico(historico):
    """Formata histórico para string (lista de dicts {role, content})."""
    if not historico:
        return ""
    partes = []
    for m in historico:
        role = m.get("role", "user")
        content = (m.get("content") or "")[:500]
        partes.append(f"[{role}]: {content}")
    return "\n".join(partes)


def montar_contexto(mensagem: str, historico=None) -> str:
    """
    Monta contexto leve antes de chamar o modelo.
    Retorna prompt completo: base + histórico (últimas 3) + mensagem do usuário.
    """
    if historico is None:
        historico = []

    ultimas = historico[-3:]
    contexto_chat = _formatar_historico(ultimas)

    if pytz:
        try:
            tz = pytz.timezone("America/Sao_Paulo")
            agora = datetime.now(tz)
        except Exception:
            agora = datetime.now()
    else:
        agora = datetime.now()

    contexto_base = f"""
Você é a Yui, uma assistente integrada ao sistema local.

Data atual: {agora.strftime("%d/%m/%Y")}
Hora atual: {agora.strftime("%H:%M")}

Regras:
- Seja objetiva
- Priorize respostas curtas
- Use ferramentas locais quando possível
"""

    prompt_final = f"""
{contexto_base.strip()}

Histórico recente:
{contexto_chat or "(nenhum)"}

Usuário:
{mensagem}
"""
    return prompt_final.strip()


def contexto_base_sistema() -> str:
    """
    Retorna apenas o bloco base (data, hora, regras) para injetar como system message.
    Útil quando o histórico já está em msgs.
    """
    if pytz:
        try:
            tz = pytz.timezone("America/Sao_Paulo")
            agora = datetime.now(tz)
        except Exception:
            agora = datetime.now()
    else:
        agora = datetime.now()

    return (
        f"Data atual: {agora.strftime('%d/%m/%Y')} | Hora: {agora.strftime('%H:%M')}. "
        "Seja objetiva, priorize respostas curtas, use ferramentas locais quando possível."
    )
