"""
Memória local de mensagens do chat.
Armazena últimas 100 mensagens em %LOCALAPPDATA%/Yui/chat_memory.json.
Cada mensagem: id, autor, conteudo, tipo, timestamp, resumo.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

MAX_MESSAGES = 100
_PATH: Optional[str] = None


def _get_path() -> str:
    global _PATH
    if _PATH is not None:
        return _PATH
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    dir_path = os.path.join(base, "Yui")
    try:
        os.makedirs(dir_path, exist_ok=True)
    except OSError:
        pass
    _PATH = os.path.join(dir_path, "chat_memory.json")
    return _PATH


def _resumo(conteudo: str, max_len: int = 80) -> str:
    s = (conteudo or "").strip().replace("\n", " ")
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


class ChatMemory:
    """Memória de mensagens do chat (últimas 100)."""

    def __init__(self) -> None:
        self._messages: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        path = _get_path()
        if not os.path.isfile(path):
            self._messages = []
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._messages = json.load(f)
        except Exception:
            self._messages = []
        if not isinstance(self._messages, list):
            self._messages = []

    def _save(self) -> None:
        path = _get_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._messages[-MAX_MESSAGES:], f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def add_message(self, autor: str, conteudo: str, tipo: str = "texto") -> Dict[str, Any]:
        """Adiciona mensagem e retorna o objeto criado (com id)."""
        msg = {
            "id": str(uuid.uuid4()),
            "autor": autor,
            "conteudo": conteudo or "",
            "tipo": tipo if tipo in ("texto", "codigo", "arquivo", "relatorio") else "texto",
            "timestamp": datetime.now().isoformat(),
            "resumo": _resumo(conteudo),
        }
        self._messages.append(msg)
        self._save()
        return msg

    def get_message_by_id(self, id_msg: str) -> Optional[Dict[str, Any]]:
        """Retorna mensagem por id ou None."""
        for m in self._messages:
            if m.get("id") == id_msg:
                return m
        return None

    def search_by_keywords(self, palavras: List[str]) -> List[Dict[str, Any]]:
        """Busca mensagens que contenham todas as palavras (case insensitive)."""
        if not palavras:
            return []
        lower = [p.lower() for p in palavras if p]
        out = []
        for m in self._messages:
            text = (m.get("conteudo") or "") + " " + (m.get("resumo") or "")
            if all(w in text.lower() for w in lower):
                out.append(m)
        return out

    def get_last_from_yui(self) -> Optional[Dict[str, Any]]:
        """Retorna a última mensagem da Yui."""
        for m in reversed(self._messages):
            if m.get("autor") == "yui":
                return m
        return None

    def get_context(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Retorna as últimas `limit` mensagens (para contexto)."""
        return list(self._messages[-limit:])


_default_memory: Optional[ChatMemory] = None


def get_chat_memory() -> ChatMemory:
    """Singleton da memória de chat."""
    global _default_memory
    if _default_memory is None:
        _default_memory = ChatMemory()
    return _default_memory
