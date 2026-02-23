"""
Rotas de administração — logs, usuários, estatísticas.
Acesso restrito a ADMIN_EMAILS ou ADMIN_USER_IDS (config).
"""

import os
from pathlib import Path

from flask import Blueprint, jsonify, request

try:
    from config import settings
    BASE_DIR = settings.BASE_DIR
    LOGS_DIR = BASE_DIR / "logs"
    ADMIN_EMAILS = set(
        e.strip().lower()
        for e in (os.environ.get("ADMIN_EMAILS") or getattr(settings, "ADMIN_EMAILS", "") or "").split(",")
        if e.strip()
    )
    ADMIN_USER_IDS = set(
        u.strip()
        for u in (os.environ.get("ADMIN_USER_IDS") or getattr(settings, "ADMIN_USER_IDS", "") or "").split(",")
        if u.strip()
    )
except Exception:
    BASE_DIR = Path(__file__).resolve().parents[2]
    LOGS_DIR = BASE_DIR / "logs"
    ADMIN_EMAILS = set()
    ADMIN_USER_IDS = set()

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def _is_admin(user_id: str, email: str = "") -> bool:
    """Verifica se o usuário é admin (email ou user_id na lista)."""
    if not user_id:
        return False
    if user_id in ADMIN_USER_IDS:
        return True
    if email and email.strip().lower() in ADMIN_EMAILS:
        return True
    try:
        from core.user_profile import get_user_profile
        profile = get_user_profile(user_id)
        if profile and profile.get("email", "").strip().lower() in ADMIN_EMAILS:
            return True
    except Exception:
        pass
    try:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client("service")
        if sb:
            r = sb.table("users_profile").select("email").eq("id", user_id).limit(1).execute()
            if r.data and r.data[0].get("email", "").strip().lower() in ADMIN_EMAILS:
                return True
    except Exception:
        pass
    return False


def _require_admin():
    """Extrai user_id do request e verifica se é admin. Retorna (user_id, error_response) ou (user_id, None)."""
    user_id = request.args.get("user_id") or (request.get_json(silent=True) or {}).get("user_id") or request.headers.get("X-User-Id")
    email = (request.get_json(silent=True) or {}).get("email") or request.headers.get("X-User-Email", "")
    if not user_id:
        return None, (jsonify({"error": "user_id obrigatório"}), 401)
    if not _is_admin(user_id, email):
        return None, (jsonify({"error": "Acesso negado. Apenas administradores."}), 403)
    return user_id, None


# ==========================================================
# LOGS
# ==========================================================

@admin_bp.get("/logs")
def api_admin_logs():
    """Lista últimas linhas do log (yui.log). Query: lines (default 200), user_id."""
    user_id, err = _require_admin()
    if err:
        return err[0], err[1]
    lines = min(int(request.args.get("lines", 200)), 2000)
    log_path = LOGS_DIR / "yui.log"
    if not log_path.exists():
        return jsonify({"ok": True, "lines": [], "path": str(log_path), "message": "Arquivo de log não existe"})
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
        tail = all_lines[-lines:] if len(all_lines) > lines else all_lines
        return jsonify({"ok": True, "lines": tail, "path": str(log_path), "total": len(all_lines)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@admin_bp.delete("/logs")
def api_admin_logs_clear():
    """Limpa o arquivo de log (trunca para 0 bytes). Body: user_id."""
    user_id, err = _require_admin()
    if err:
        return err[0], err[1]
    log_path = LOGS_DIR / "yui.log"
    if not log_path.exists():
        return jsonify({"ok": True, "message": "Log já estava vazio"})
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("")
        return jsonify({"ok": True, "message": "Log limpo"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ==========================================================
# USUÁRIOS
# ==========================================================

@admin_bp.get("/users")
def api_admin_users():
    """Lista usuários (Supabase Auth + users_profile). Requer service key."""
    user_id, err = _require_admin()
    if err:
        return err[0], err[1]
    try:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client("service")
        if not sb:
            return jsonify({"ok": False, "error": "Supabase não configurado"}), 503
        users = []
        try:
            r = sb.table("users_profile").select("id, email").execute()
            if r.data:
                users = [
                    {"id": str(row.get("id", "")), "email": row.get("email", "") or "", "created_at": "", "last_sign_in_at": ""}
                    for row in r.data
                ]
            auth_users = []
            try:
                ar = sb.auth.admin.list_users()
                auth_users = getattr(ar, "users", []) or []
            except Exception:
                pass
            if auth_users:
                seen = {u["id"] for u in users}
                for u in auth_users:
                    uid = str(getattr(u, "id", "") or (u.get("id", "") if isinstance(u, dict) else ""))
                    if uid and uid not in seen:
                        users.append({
                            "id": uid,
                            "email": getattr(u, "email", "") or (u.get("email", "") if isinstance(u, dict) else ""),
                            "created_at": str(getattr(u, "created_at", "") or (u.get("created_at", "") if isinstance(u, dict) else "")),
                            "last_sign_in_at": str(getattr(u, "last_sign_in_at", "") or (u.get("last_sign_in_at", "") if isinstance(u, dict) else "")),
                        })
                        seen.add(uid)
            if not users:
                users = [{"id": "—", "email": "Nenhum usuário encontrado", "created_at": "", "last_sign_in_at": ""}]
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
        chats_count = {}
        try:
            r_chats = sb.table("chats").select("user_id").execute()
            for row in (r_chats.data or []):
                uid = row.get("user_id")
                if uid:
                    chats_count[uid] = chats_count.get(uid, 0) + 1
        except Exception:
            pass
        for u in users:
            u["chats_count"] = chats_count.get(u.get("id", ""), 0)
        return jsonify({"ok": True, "users": users})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ==========================================================
# ESTATÍSTICAS
# ==========================================================

@admin_bp.get("/stats")
def api_admin_stats():
    """Estatísticas gerais: chats, mensagens, usuários."""
    user_id, err = _require_admin()
    if err:
        return err[0], err[1]
    try:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client("service")
        stats = {"chats": 0, "messages": 0, "users": 0}
        if sb:
            try:
                r = sb.table("chats").select("id", count="exact").execute()
                stats["chats"] = r.count if hasattr(r, "count") and r.count is not None else len(r.data or [])
            except Exception:
                pass
            try:
                r = sb.table("messages").select("id", count="exact").execute()
                stats["messages"] = r.count if hasattr(r, "count") and r.count is not None else len(r.data or [])
            except Exception:
                pass
            try:
                r = sb.auth.admin.list_users()
                stats["users"] = len(getattr(r, "users", []) or [])
            except Exception:
                try:
                    r = sb.table("users_profile").select("id", count="exact").execute()
                    stats["users"] = r.count if hasattr(r, "count") and r.count is not None else len(r.data or [])
                except Exception:
                    pass
        return jsonify({"ok": True, "stats": stats})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ==========================================================
# CHATS (excluir como admin)
# ==========================================================

@admin_bp.delete("/chat/<chat_id>")
def api_admin_delete_chat(chat_id):
    """Exclui um chat (e mensagens) como admin. Body: user_id."""
    _, err = _require_admin()
    if err:
        return err[0], err[1]
    if not chat_id:
        return jsonify({"error": "chat_id obrigatório"}), 400
    try:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client("service")
        if not sb:
            return jsonify({"ok": False, "error": "Supabase não configurado"}), 503
        sb.table("messages").delete().eq("chat_id", chat_id).execute()
        sb.table("chats").delete().eq("id", chat_id).execute()
        return jsonify({"ok": True, "message": "Chat excluído"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ==========================================================
# CHECK (verificar se usuário é admin)
# ==========================================================

@admin_bp.get("/check")
def api_admin_check():
    """Verifica se o user_id é admin. Query: user_id."""
    user_id = request.args.get("user_id") or (request.get_json(silent=True) or {}).get("user_id")
    if not user_id:
        return jsonify({"ok": False, "admin": False, "error": "user_id obrigatório"}), 400
    return jsonify({"ok": True, "admin": _is_admin(user_id)})
