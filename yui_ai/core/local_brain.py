"""
Local Brain — Responde coisas simples SEM gastar tokens.
Perguntas como "que horas", "oi", "como zipar" → resposta instantânea, zero API.
"""

from datetime import datetime

try:
    import pytz
except ImportError:
    pytz = None


def responder_local(pergunta: str):
    """Retorna resposta local se a pergunta for trivial; None caso contrário."""
    if not pergunta:
        return None

    p = pergunta.lower().strip()

    # =========================
    # HORAS / DATA
    # =========================
    if "que horas" in p or "horario" in p or "horário" in p:
        if pytz:
            tz = pytz.timezone("America/Sao_Paulo")
            agora = datetime.now(tz)
        else:
            agora = datetime.now()
        return f"Horário atual (Brasília): {agora.strftime('%d/%m/%Y %H:%M:%S')}"

    if "que dia" in p or "data de hoje" in p:
        if pytz:
            tz = pytz.timezone("America/Sao_Paulo")
            hoje = datetime.now(tz)
        else:
            hoje = datetime.now()
        return f"Hoje é {hoje.strftime('%d/%m/%Y')}"

    # =========================
    # SAUDAÇÕES
    # =========================
    if p in ["oi", "ola", "olá", "oi yui", "ola yui", "olá yui"]:
        return "Olá! Estou pronta para ajudar você 🚀"

    if "como vc esta" in p or "como você está" in p or "como voce esta" in p:
        return "Estou funcionando perfeitamente no servidor 😄"

    # =========================
    # COMPACTAR ARQUIVO
    # =========================
    if "compactar arquivo" in p or "zipar arquivo" in p:
        return (
            "Para compactar via terminal use:\n"
            "zip -r arquivo.zip pasta/\n\n"
            "Isso cria um .zip com tudo dentro."
        )

    # =========================
    # BAIXAR ARQUIVO
    # =========================
    if "baixar arquivo" in p:
        return (
            "Você pode baixar usando wget:\n"
            "wget URL_DO_ARQUIVO"
        )

    return None
