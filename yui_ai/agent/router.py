# =============================================================
# Intent Router — detecta intenção da mensagem (upload, análise, chat)
# =============================================================


def detect_intent(text: str) -> str:
    if not text or not isinstance(text, str):
        return "chat"
    t = text.lower().strip()
    if "upload" in t or "enviar arquivo" in t or "anexar" in t:
        return "upload"
    if "codigo" in t or "código" in t or "analisar" in t or "analise" in t or "análise" in t:
        return "code_analysis"
    return "chat"
