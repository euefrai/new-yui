"""
Intent Router — Porteiro antes da IA.
Decide o tipo de pensamento primeiro: Local, Cache, Tools ou LLM.
"""

from typing import Literal

Rota = Literal["time", "zip_builder", "terminal", "deploy", "web_search", "llm"]


def decidir_rota(texto: str) -> Rota:
    """Define a rota da mensagem antes de qualquer processamento."""
    if not texto or not isinstance(texto, str):
        return "llm"

    t = texto.lower().strip()

    # comandos locais rápidos
    if "hora" in t or "horas" in t or "horário" in t or "horario" in t:
        return "time"

    if "zip" in t or "compactar" in t or "zipar" in t:
        return "zip_builder"

    if "terminal" in t or "executar" in t or "rodar" in t or "run" in t:
        return "terminal"

    if "deploy" in t or "deployar" in t:
        return "deploy"

    # busca factual na web (sem LLM)
    web_hints = [
        "pesquisar", "buscar", "o que é", "quem é", "como funciona", "o que significa",
        "brasileirão", "brasileirao", "jogos", "jogo de hoje", "jogos de hoje",
        "notícia", "noticia", "notícias", "news", "placar", "rodada",
        "playstation", "ps5", "xbox", "steam", "nintendo",
        "mais jogados", "tendência", "tendencia", "ranking",
    ]
    if any(k in t for k in web_hints):
        return "web_search"

    # pergunta geral → LLM
    return "llm"
