# =============================================================
# SessionMemory — memória por usuário (não global)
# Evita vazamento entre sessões; cada user_id tem sua própria lista.
# MAX_CONTEXT = 12 para evitar RAM infinito em servidores 2GB.
# =============================================================

from typing import Any, Dict, List

MAX_CONTEXT = 12


class SessionMemory:
    def __init__(self) -> None:
        self.sessions: Dict[str, List[Dict[str, Any]]] = {}

    def get(self, user_id: str) -> List[Dict[str, Any]]:
        return self.sessions.setdefault(user_id, [])

    def add(self, user_id: str, role: str, content: str) -> None:
        lst = self.sessions.setdefault(user_id, [])
        lst.append({"role": role, "content": content})
        self.sessions[user_id] = lst[-MAX_CONTEXT:]

    def clear(self, user_id: str) -> None:
        if user_id in self.sessions:
            self.sessions[user_id] = []


memory = SessionMemory()
