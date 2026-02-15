"""
Interface única de memória: save_message(), load_history().
Se USE_SUPABASE_MEMORY=true usa Supabase; senão usa JSON local.
Remove acesso direto ao JSON das rotas; uma fonte de verdade.
"""
import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from config.settings import DATA_DIR, USE_SUPABASE_MEMORY
except Exception:
    USE_SUPABASE_MEMORY = False
    DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

_LOCAL_FILE = DATA_DIR / "chats.json"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _read_local() -> Dict[str, Any]:
    _ensure_data_dir()
    if not _LOCAL_FILE.exists():
        return {"chats": {}, "messages_by_chat": {}}
    try:
        with open(_LOCAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"chats": {}, "messages_by_chat": {}}


def _write_local(data: Dict[str, Any]) -> None:
    _ensure_data_dir()
    with open(_LOCAL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_message(
    chat_id: str,
    role: str,
    content: str,
    user_id: Optional[str] = None,
) -> None:
    """Salva uma mensagem no chat. Interface única (Supabase ou JSON local)."""
    if USE_SUPABASE_MEMORY:
        from core.memory import save_message as _save
        _save(chat_id, role, content or "", user_id)
        return
    data = _read_local()
    if chat_id not in data["messages_by_chat"]:
        data["messages_by_chat"][chat_id] = []
    data["messages_by_chat"][chat_id].append({
        "id": str(uuid.uuid4()),
        "role": role,
        "content": content or "",
    })
    _write_local(data)


def load_history(
    chat_id: str,
    user_id: Optional[str] = None,
    limit: Optional[int] = 100,
) -> List[Dict[str, Any]]:
    """Carrega histórico de mensagens do chat. Interface única. limit=100 reduz RAM."""
    if USE_SUPABASE_MEMORY:
        from core.memory import get_messages
        return get_messages(chat_id, user_id, limit=limit) or []
    data = _read_local()
    if user_id and data.get("chats", {}).get(chat_id, {}).get("user_id") != user_id:
        return []
    msgs = data.get("messages_by_chat", {}).get(chat_id, [])
    if limit and len(msgs) > limit:
        return msgs[-limit:]
    return msgs


def chat_belongs_to_user(chat_id: str, user_id: str) -> bool:
    """True se o chat existe e pertence ao user_id."""
    if USE_SUPABASE_MEMORY:
        from core.memory import chat_belongs_to_user as _check
        return bool(_check(chat_id, user_id))
    data = _read_local()
    return data.get("chats", {}).get(chat_id, {}).get("user_id") == user_id


def get_chats(user_id: str) -> List[Dict[str, Any]]:
    """Lista chats do usuário."""
    if USE_SUPABASE_MEMORY:
        from core.memory import get_chats as _get
        return _get(user_id) or []
    data = _read_local()
    return [
        {"id": cid, **c}
        for cid, c in (data.get("chats") or {}).items()
        if c.get("user_id") == user_id
    ]


def create_chat(user_id: str) -> Optional[Dict[str, Any]]:
    """Cria um novo chat. Retorna o chat ou None."""
    if USE_SUPABASE_MEMORY:
        from core.memory import create_chat as _create
        return _create(user_id)
    data = _read_local()
    if "chats" not in data:
        data["chats"] = {}
    cid = str(uuid.uuid4())
    data["chats"][cid] = {"user_id": user_id, "titulo": "Novo chat"}
    data.setdefault("messages_by_chat", {})[cid] = []
    _write_local(data)
    return {"id": cid, "user_id": user_id, "titulo": "Novo chat"}


def update_chat_title(chat_id: str, titulo: str, user_id: Optional[str] = None) -> None:
    if USE_SUPABASE_MEMORY:
        from core.memory import update_chat_title as _upd
        _upd(chat_id, titulo, user_id)
        return
    if user_id and not chat_belongs_to_user(chat_id, user_id):
        return
    data = _read_local()
    if chat_id in data.get("chats", {}):
        data["chats"][chat_id]["titulo"] = titulo
        _write_local(data)


def message_belongs_to_user(message_id: str, user_id: str) -> bool:
    if USE_SUPABASE_MEMORY:
        from core.memory import message_belongs_to_user as _check
        return bool(_check(message_id, user_id))
    data = _read_local()
    for cid, msgs in data.get("messages_by_chat", {}).items():
        for m in msgs:
            if m.get("id") == message_id:
                return data.get("chats", {}).get(cid, {}).get("user_id") == user_id
    return False


def get_message_for_edit(message_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    if USE_SUPABASE_MEMORY:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client("service")
        if not sb:
            return None
        try:
            r = sb.table("messages").select("*").eq("id", message_id).limit(1).execute()
            if not r.data or not message_belongs_to_user(message_id, user_id):
                return None
            return r.data[0]
        except Exception:
            return None
    data = _read_local()
    for cid, msgs in data.get("messages_by_chat", {}).items():
        if data.get("chats", {}).get(cid, {}).get("user_id") != user_id:
            continue
        for m in msgs:
            if m.get("id") == message_id:
                return m
    return None


def update_message(message_id: str, content: str, user_id: str) -> bool:
    if USE_SUPABASE_MEMORY:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client("service")
        if not sb or not message_belongs_to_user(message_id, user_id):
            return False
        try:
            sb.table("messages").update({"content": content}).eq("id", message_id).execute()
            return True
        except Exception:
            return False
    data = _read_local()
    for cid, msgs in data.get("messages_by_chat", {}).items():
        if data.get("chats", {}).get(cid, {}).get("user_id") != user_id:
            continue
        for i, m in enumerate(msgs):
            if m.get("id") == message_id:
                data["messages_by_chat"][cid][i]["content"] = content
                _write_local(data)
                return True
    return False


def remove_message(message_id: str, user_id: str) -> bool:
    if USE_SUPABASE_MEMORY:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client("service")
        if not sb or not message_belongs_to_user(message_id, user_id):
            return False
        try:
            sb.table("messages").delete().eq("id", message_id).execute()
            return True
        except Exception:
            return False
    data = _read_local()
    for cid, msgs in data.get("messages_by_chat", {}).items():
        if data.get("chats", {}).get(cid, {}).get("user_id") != user_id:
            continue
        new_msgs = [m for m in msgs if m.get("id") != message_id]
        if len(new_msgs) == len(msgs):
            continue
        data["messages_by_chat"][cid] = new_msgs
        _write_local(data)
        return True
    return False


def delete_chat(chat_id: str, user_id: str) -> bool:
    if USE_SUPABASE_MEMORY:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client("service")
        if not sb or not chat_belongs_to_user(chat_id, user_id):
            return False
        try:
            sb.table("messages").delete().eq("chat_id", chat_id).execute()
            sb.table("chats").delete().eq("id", chat_id).eq("user_id", user_id).execute()
            return True
        except Exception:
            return False
    if not chat_belongs_to_user(chat_id, user_id):
        return False
    data = _read_local()
    data.get("chats", {}).pop(chat_id, None)
    data.get("messages_by_chat", {}).pop(chat_id, None)
    _write_local(data)
    return True
