# Rotas de ferramentas: listar, executar.

from flask import Blueprint, jsonify, request
from core.tools_registry import list_tools
from core.tool_runner import run_tool

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
