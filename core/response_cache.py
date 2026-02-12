# ==========================================================
# YUI RESPONSE CACHE
# Cache de respostas curtas — evita gerar de novo.
#
# Se o usuário pergunta algo repetido (oi, obrigado, etc):
# cache[prompt] -> resposta pronta
#
# Menos CPU, menos RAM, sensação de IA "inteligente".
# ==========================================================

import re
import time
from collections import OrderedDict
from threading import Lock
from typing import Optional

MAX_ENTRIES = 100
MAX_PROMPT_LEN = 80
TTL_SECONDS = 3600  # 1 hora

# Respostas padrão para prompts muito curtos (saudações, etc)
_DEFAULT_RESPONSES = {
    "oi": "Olá! Como posso ajudar?",
    "olá": "Olá! Como posso ajudar?",
    "ola": "Olá! Como posso ajudar?",
    "oi!": "Olá! Como posso ajudar?",
    "olá!": "Olá! Como posso ajudar?",
    "hey": "Oi! Em que posso ajudar?",
    "hi": "Olá! Como posso ajudar?",
    "hello": "Olá! Como posso ajudar?",
    "obrigado": "De nada! Precisa de mais alguma coisa?",
    "obrigada": "De nada! Precisa de mais alguma coisa?",
    "valeu": "Por nada! Estou à disposição.",
    "vlw": "Por nada! Estou à disposição.",
    "tchau": "Até logo! Volte quando precisar.",
    "bye": "Até logo! Volte quando precisar.",
    "tudo bem?": "Tudo ótimo! E você? Em que posso ajudar?",
    "tudo bem": "Tudo bem! E você? Em que posso ajudar?",
    "como vai?": "Tudo certo! E você? Preciso de algo?",
}

_cache: OrderedDict = OrderedDict()
_lock = Lock()


def _normalize_key(text: str) -> str:
    """Normaliza o prompt para chave de cache."""
    if not text or not isinstance(text, str):
        return ""
    s = re.sub(r"\s+", " ", text.lower().strip())
    return s[:MAX_PROMPT_LEN] if len(s) > MAX_PROMPT_LEN else s


def get(prompt: str) -> Optional[str]:
    """
    Retorna resposta em cache se existir e não expirada.
    Também verifica respostas padrão para saudações.
    """
    key = _normalize_key(prompt)
    if not key:
        return None

    # Resposta padrão (sem chamar IA)
    if key in _DEFAULT_RESPONSES:
        return _DEFAULT_RESPONSES[key]

    with _lock:
        if key not in _cache:
            return None
        entry = _cache[key]
        if TTL_SECONDS > 0 and (time.time() - entry["ts"]) > TTL_SECONDS:
            del _cache[key]
            return None
        # move to end (LRU)
        _cache.move_to_end(key)
        return entry["response"]


def set(prompt: str, response: str) -> None:
    """Armazena resposta no cache."""
    key = _normalize_key(prompt)
    if not key or len(key) < 2:
        return
    # Não cachear respostas padrão (já estão em _DEFAULT_RESPONSES)
    if key in _DEFAULT_RESPONSES:
        return
    with _lock:
        _cache[key] = {"response": response, "ts": time.time()}
        _cache.move_to_end(key)
        while len(_cache) > MAX_ENTRIES:
            _cache.popitem(last=False)


def should_cache(prompt: str) -> bool:
    """Verifica se o prompt é curto o suficiente para cache."""
    key = _normalize_key(prompt)
    if not key:
        return False
    # Sempre usar resposta padrão para saudações conhecidas
    if key in _DEFAULT_RESPONSES:
        return True
    return len(key) <= MAX_PROMPT_LEN


def clear() -> None:
    """Limpa o cache (útil para testes)."""
    with _lock:
        _cache.clear()


def size() -> int:
    """Retorna número de entradas no cache."""
    with _lock:
        return len(_cache)
