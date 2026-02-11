# =============================================================
# SessionMemory — memória por usuário (não global)
# Evita vazamento entre sessões; cada user_id tem sua própria lista.
# =============================================================

from typing import Any, Dict, List


class SessionMemory:
    def __init__(self) -> None:
        self.sessions: Dict[str, List[Dict[str, Any]]] = {}

    def get(self, user_id: str) -> List[Dict[str, Any]]:
        return self.sessions.setdefault(user_id, [])

    def add(self, user_id: str, role: str, content: str) -> None:
        self.sessions.setdefault(user_id, []).append({
            "role": role,
            "content": content,
        })

    def clear(self, user_id: str) -> None:
        if user_id in self.sessions:
            self.sessions[user_id] = []


memory = SessionMemory()
