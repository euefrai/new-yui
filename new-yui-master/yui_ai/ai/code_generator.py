"""
Geração automática de código a partir de pedido em linguagem natural.
Detecta linguagem (java, javascript, python, html, css) e retorna resposta estruturada.
NUNCA executa código gerado — apenas texto estático.
"""

import os
import re
from typing import Optional, Tuple

# Linguagens detectáveis no texto do pedido
LANG_KEYWORDS = {
    "java": r"\bjava\b",
    "javascript": r"\bjavascript\b|\bjs\b",
    "python": r"\bpython\b|\bpy\b",
    "html": r"\bhtml\b",
    "css": r"\bcss\b",
}

PEDIDO_CODIGO_PATTERNS = [
    r"\bcri[eá]\b", r"\bfa[çc](a|er)\b", r"\bgerar\b", r"\bescrev(a|er)\b",
    r"\bimplement(a|ar)\b", r"\bcódigo\b", r"\bcode\b", r"\bcalculadora\b",
    r"\bfunção\b", r"\bscript\b", r"\bpágina\b", r"\bcomponente\b",
]


def _detectar_linguagem(texto: str) -> Optional[str]:
    """Detecta linguagem mencionada no pedido. Retorna None se não identificar."""
    t = (texto or "").lower()
    for lang, pattern in LANG_KEYWORDS.items():
        if re.search(pattern, t, re.I):
            return lang
    return None


def eh_pedido_de_codigo(texto: str) -> bool:
    """Retorna True se o texto parecer um pedido de geração de código."""
    if not texto or len(texto.strip()) < 4:
        return False
    t = (texto or "").lower()
    return any(re.search(p, t, re.I) for p in PEDIDO_CODIGO_PATTERNS)


def gerar_codigo(pedido: str) -> Tuple[bool, str, Optional[str]]:
    """
    Gera resposta estruturada com código conforme o pedido.
    Retorna (sucesso, texto_resposta, erro).
    Formato: 📦 Título | 🧠 Explicação | 💻 Código | ⚙️ Melhorias possíveis.
    """
    from yui_ai.core.ai_engine import _gerar_resposta_codigo_ia

    lang = _detectar_linguagem(pedido)
    linguagem = lang or "python"

    sucesso, texto, erro = _gerar_resposta_codigo_ia(pedido, linguagem)
    return sucesso, texto, erro
