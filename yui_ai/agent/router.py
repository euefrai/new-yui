# =============================================================
# Intent Router — detecta intenção da mensagem (upload, análise, chat)
# =============================================================


def detect_intent(text: str) -> str:
    if not text or not isinstance(text, str):
        return "chat"
    t = text.lower().strip()
    if "upload" in t or "enviar arquivo" in t or "anexar" in t:
        return "upload"
    # code_analysis só quando o usuário pede ANÁLISE de código (não quando pede para criar/gerar)
    if "analisar" in t or "analise" in t or "análise" in t or "analisa " in t:
        return "code_analysis"
    # "cria um código", "crie um codigo", "gera código" -> chat (agente gera o código)
    return "chat"
