# ==========================================================
# YUI TASK PLANNER AGENT
# Cria um plano de execução antes da resposta principal
# ==========================================================


def criar_plano(mensagem_usuario: str) -> str:
    """
    Analisa o pedido do usuário e gera um plano estruturado.
    Não usa IA aqui — é leve e rápido.
    """
    texto = (mensagem_usuario or "").lower().strip()
    etapas: list[str] = []

    # heurísticas simples
    if "script" in texto or "codigo" in texto or "código" in texto:
        etapas.append("Entender o objetivo técnico do usuário")
        etapas.append("Definir estrutura do código")
        etapas.append("Gerar implementação funcional")

    if "corrigir" in texto or "erro" in texto or "bug" in texto:
        etapas.append("Identificar possível causa do erro")
        etapas.append("Aplicar correção segura")
        etapas.append("Explicar a solução")

    if "melhorar" in texto or "profissional" in texto:
        etapas.append("Analisar arquitetura atual")
        etapas.append("Aplicar boas práticas")
        etapas.append("Sugerir melhorias futuras")

    if "sistema" in texto or "completo" in texto or "login" in texto or "upload" in texto:
        etapas.append("Definir escopo e requisitos")
        etapas.append("Estruturar componentes (front/back)")
        etapas.append("Implementar e integrar")

    if not etapas:
        etapas.append("Interpretar pedido")
        etapas.append("Gerar melhor resposta possível")

    plano = "\n".join(f"- {e}" for e in etapas)
    return f"""
Plano interno da Yui para responder:

{plano}
"""
