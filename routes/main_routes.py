# Rotas principais: index, estáticos (web, generated), clear_chat.

import os
from flask import Blueprint, request, render_template, send_from_directory, jsonify, session

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "web")
GENERATED_DIR = os.path.join(BASE_DIR, "generated_projects")


def _supabase_url():
    return (os.environ.get("SUPABASE_URL") or "").strip()


def _supabase_public_key():
    return (
        (os.environ.get("SUPABASE_PUBLISHABLE_KEY") or "").strip()
        or (os.environ.get("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY") or "").strip()
        or (os.environ.get("SUPABASE_KEY") or "").strip()
    )


main_bp = Blueprint("main", __name__)


@main_bp.route("/", methods=["GET", "OPTIONS"])
def index():
    if request.method == "OPTIONS":
        return "", 204
    return render_template(
        "index.html",
        supabase_url=_supabase_url(),
        supabase_key=_supabase_public_key(),
    )


@main_bp.get("/web/<path:path>")
def web_static(path: str):
    return send_from_directory(WEB_DIR, path)


@main_bp.route("/generated/<path:path>")
def generated_static(path: str):
    return send_from_directory(GENERATED_DIR, path)


@main_bp.route("/download/<path:filename>")
def download_file(filename: str):
    """Serve arquivos de generated_projects para download (ex.: .zip do projeto)."""
    return send_from_directory(GENERATED_DIR, filename, as_attachment=True)


@main_bp.route("/clear_chat", methods=["POST"])
def clear_chat():
    user_id = session.get("user_id")
    if not user_id:
        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id obrigatório", "status": "error"}), 400
    try:
        from yui_ai.memory.session_memory import memory
        memory.clear(user_id)
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500
