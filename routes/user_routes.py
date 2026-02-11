# Rotas de usuário: perfil.

from flask import Blueprint, jsonify, request
from core.user_profile import get_user_profile, upsert_user_profile

user_bp = Blueprint("user", __name__, url_prefix="")


@user_bp.route("/profile", methods=["POST"])
def api_user_profile():
    """
    Body: user_id (obrigatório), email, nivel_tecnico, linguagens_pref, modo_resposta.
    """
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "user_id obrigatório"}), 400
    ok = upsert_user_profile(
        user_id=user_id,
        email=data.get("email") or "",
        nivel_tecnico=data.get("nivel_tecnico"),
        linguagens_pref=data.get("linguagens_pref"),
        modo_resposta=data.get("modo_resposta"),
    )
    if not ok:
        return jsonify({"success": False, "error": "Falha ao salvar perfil"}), 500
    profile = get_user_profile(user_id)
    return jsonify({"success": True, "profile": profile})


@user_bp.route("/profile/get", methods=["POST"])
def api_user_profile_get():
    """Retorna o perfil do usuário (body: user_id)."""
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "user_id obrigatório"}), 400
    profile = get_user_profile(user_id)
    return jsonify({"success": True, "profile": profile})
