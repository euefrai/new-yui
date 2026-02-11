# Rotas de API: index, estáticos, download, clear_chat, upload, analyze, tools.

from flask import Blueprint, request, render_template, send_from_directory, jsonify, session

from config.settings import (
    GENERATED_PROJECTS_DIR,
    SUPABASE_ANON_KEY,
    SUPABASE_URL,
    WEB_LEGACY_DIR,
)
from core.tool_runner import run_tool
from core.tools_registry import list_tools


# --- Main (index, estáticos, download, clear_chat) ---
main_bp = Blueprint("main", __name__)


@main_bp.route("/", methods=["GET", "OPTIONS"])
def index():
    if request.method == "OPTIONS":
        return "", 204
    return render_template(
        "index.html",
        supabase_url=SUPABASE_URL or "",
        supabase_key=SUPABASE_ANON_KEY or "",
    )


@main_bp.get("/web/<path:path>")
def web_static(path: str):
    return send_from_directory(str(WEB_LEGACY_DIR), path)


@main_bp.route("/generated/<path:path>")
def generated_static(path: str):
    return send_from_directory(str(GENERATED_PROJECTS_DIR), path)


@main_bp.route("/download/<path:filename>")
def download_file(filename: str):
    """Serve arquivos de generated_projects para download (ex.: .zip do projeto)."""
    return send_from_directory(str(GENERATED_PROJECTS_DIR), filename, as_attachment=True)


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


# --- File (upload, analyze) ---
file_bp = Blueprint("file", __name__, url_prefix="")


@file_bp.route("/upload", methods=["POST", "OPTIONS"])
def api_upload():
    if request.method == "OPTIONS":
        return "", 204
    try:
        if "file" not in request.files:
            return jsonify({"error": "Nenhum arquivo enviado."}), 400
        f = request.files["file"]
        if not f or not f.filename:
            return jsonify({"error": "Arquivo inválido."}), 400
        try:
            content = f.read()
        except Exception as e:
            return jsonify({"error": str(e)}), 400

        result = run_tool(
            "analisar_arquivo",
            {"filename": f.filename, "content": content.decode("utf-8", errors="ignore")},
        )
        if not result.get("ok"):
            return jsonify({"error": result.get("error") or "Erro na análise."}), 400
        text = (result.get("result") or {}).get("text") or ""
        if not text:
            return jsonify({"error": "Relatório vazio."}), 400
        return jsonify({"response": text})
    except Exception as e:
        return jsonify({"error": str(e), "response": None}), 500


@file_bp.post("/analyze-file")
def api_analyze_file():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "Nenhum arquivo enviado."}), 400
    f = request.files["file"]
    if not f or not f.filename:
        return jsonify({"success": False, "error": "Arquivo inválido."}), 400
    try:
        content = f.read()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400
    result = run_tool(
        "analisar_arquivo",
        {"filename": f.filename, "content": content.decode("utf-8", errors="ignore")},
    )
    if not result.get("ok"):
        return jsonify({"success": False, "error": result.get("error")}), 400
    report = (result.get("result") or {}).get("report")
    if not report:
        return jsonify({"success": False, "error": "Relatório vazio."}), 400
    return jsonify({"success": True, "report": report})


# --- Tool (listar, executar) ---
tool_bp = Blueprint("tool", __name__, url_prefix="")


@tool_bp.route("", methods=["GET"])
@tool_bp.route("/", methods=["GET"])
def api_list_tools():
    return jsonify(list_tools())


@tool_bp.route("/run", methods=["POST"])
def api_run_tool():
    """
    Body: name (obrigatório), args (dict).
    """
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    args = data.get("args") or {}
    if not name:
        return jsonify({"ok": False, "result": None, "error": "name obrigatório"}), 400
    result = run_tool(name, args)
    status = 200 if result.get("ok") else 400
    return jsonify(result), status
