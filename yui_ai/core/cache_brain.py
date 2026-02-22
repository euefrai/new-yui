"""
Cache Brain (Token Shield) — guarda respostas e reutiliza automaticamente.
Perguntas repetidas = ZERO tokens. Resposta instantânea.
"""

import hashlib
from collections import OrderedDict
from threading import Lock
from typing import Optional

# Cache em memória com LRU (evita crescimento infinito)
MAX_ENTRIES = 500
_cache: OrderedDict = OrderedDict()
_lock = Lock()


def gerar_hash(texto: str) -> str:
    """Gera chave MD5 a partir do texto normalizado."""
    if not texto or not isinstance(texto, str):
        return ""
    s = texto.lower().strip()
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def gerar_chave_cache(user_id: str, pergunta: str, resumo_contexto: Optional[str] = None) -> str:
    """Chave única: user_id + mensagem + resumo_contexto."""
    parts = [str(user_id or ""), (pergunta or "").strip(), (resumo_contexto or "").strip()]
    combined = "|".join(parts)
    return hashlib.md5(combined.encode("utf-8")).hexdigest()


def buscar_cache(pergunta: str, user_id: Optional[str] = None, resumo_contexto: Optional[str] = None) -> Optional[str]:
    """Retorna resposta em cache se existir. Chave: user_id + pergunta + resumo."""
    chave = gerar_chave_cache(user_id or "", pergunta, resumo_contexto) if user_id or resumo_contexto else gerar_hash(pergunta)
    if not chave:
        return None
    with _lock:
        if chave not in _cache:
            return None
        _cache.move_to_end(chave)  # LRU
        return _cache[chave]


MAX_RESPOSTA_LEN = 15000  # não cachear respostas gigantes (ex.: código grande)


def salvar_cache(pergunta: str, resposta: str, user_id: Optional[str] = None, resumo_contexto: Optional[str] = None) -> None:
    """Armazena no cache. Chave: user_id + pergunta + resumo_contexto."""
    if not resposta or not isinstance(resposta, str):
        return
    if len(resposta) > MAX_RESPOSTA_LEN:
        return
    chave = gerar_chave_cache(user_id or "", pergunta, resumo_contexto) if user_id or resumo_contexto else gerar_hash(pergunta)
    if not chave:
        return
    with _lock:
        _cache[chave] = resposta
        _cache.move_to_end(chave)
        while len(_cache) > MAX_ENTRIES:
            _cache.popitem(last=False)


def limpar_cache() -> None:
    """Limpa o cache (útil para testes)."""
    with _lock:
        _cache.clear()


def tamanho_cache() -> int:
    """Retorna número de entradas no cache."""
    with _lock:
        return len(_cache)
