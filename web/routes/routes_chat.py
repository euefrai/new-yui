# Rotas de chat: listar, criar, mensagens, stream, título, delete, edit message.
# Regra: rotas NÃO importam yui_ai; apenas services e config.

import json

from flask import Blueprint, jsonify, request, Response, stream_with_context, session

from services.chat_service import (
    chat_pertence_usuario,
    criar_chat as svc_criar_chat,
    listar_chats,
    carregar_historico,
    atualizar_titulo_chat,
    deletar_chat,
    mensagem_pertence_usuario,
    obter_mensagem_para_edicao,
    atualizar_mensagem,
    remover_mensagem,
    supabase_available,
)
from services.ai_service import (
    gerar_titulo_chat,
    handle_chat_stream,
    improve_message,
    processar_mensagem_sync,
)


chat_bp = Blueprint("chat", __name__, url_prefix="")


@chat_bp.route("/chats/<user_id>")
def api_get_chats(user_id):
    return jsonify(listar_chats(user_id))


@chat_bp.route("/chat/new", methods=["POST"])
def api_new_chat():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id obrigatório"}), 400
    chat = svc_criar_chat(user_id)
    if not chat:
        return jsonify({"error": "Falha ao criar chat"}), 500
    return jsonify(chat)


@chat_bp.route("/messages/<chat_id>")
def api_messages(chat_id):
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id obrigatório (query: ?user_id=...)"}), 400
    if not chat_pertence_usuario(chat_id, user_id):
        return jsonify({"error": "Chat não encontrado ou não pertence ao usuário"}), 403
    return jsonify(carregar_historico(chat_id, user_id))


@chat_bp.route("/send", methods=["POST"])
def api_send():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    chat_id = data.get("chat_id")
    message = (data.get("message") or "").strip()
    model = (data.get("model") or "yui").strip().lower()
    use_async = data.get("async") or request.args.get("async") == "1"
    if model not in ("yui", "heathcliff", "auto"):
        model = "yui"
    if not user_id or not chat_id:
        return jsonify({"error": "user_id e chat_id obrigatórios"}), 400
    if not message:
        return jsonify({"error": "message obrigatória"}), 400
    if not chat_pertence_usuario(chat_id, user_id):
        return jsonify({"error": "Chat não encontrado ou não pertence ao usuário"}), 403
    try:
        from config import settings
        if use_async and getattr(settings, "USE_ASYNC_QUEUE", False):
            from core.job_queue import enqueue_chat
            job_id = enqueue_chat(user_id, chat_id, message, model=model)
            return jsonify({"status": "processando", "job_id": job_id})
        reply = processar_mensagem_sync(user_id, chat_id, message, model=model)
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e), "reply": None}), 500


@chat_bp.route("/chat/job/<job_id>")
def api_chat_job(job_id):
    """Poll do resultado de job assíncrono (quando USE_ASYNC_QUEUE=true)."""
    try:
        from core.job_queue import get_job_result
        result = get_job_result(job_id)
        if not result:
            return jsonify({"error": "job_id não encontrado"}), 404
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/chat/stream", methods=["POST", "OPTIONS"])
def api_chat_stream():
    if request.method == "OPTIONS":
        return "", 204
    try:
        data = request.get_json(silent=True) or {}
        chat_id = data.get("chat_id")
        user_id = data.get("user_id")
        message = (data.get("message") or "").strip()
        model = (data.get("model") or "yui").strip().lower()
        confirm_high_cost = bool(data.get("confirm_high_cost"))
        active_files = data.get("active_files") or []
        console_errors = data.get("console_errors") or []
        workspace_open = bool(data.get("workspace_open"))
        try:
            from core.event_bus import emit
            emit("workspace_toggled", open=workspace_open)
        except Exception:
            try:
                from core.system_state import set_workspace_open
                set_workspace_open(workspace_open)
            except Exception:
                pass
        if model not in ("yui", "heathcliff", "auto"):
            model = "yui"
        if not chat_id:
            return jsonify({"error": "chat_id obrigatório"}), 400
        if not user_id:
            return jsonify({"error": "user_id obrigatório"}), 400
        if not message:
            return jsonify({"error": "message obrigatória"}), 400
        if not chat_pertence_usuario(chat_id, user_id):
            return jsonify({"error": "Chat não encontrado ou não pertence ao usuário"}), 403

        session["user_id"] = user_id

        def generate():
            yield f"data: {json.dumps('__STATUS__:thinking')}\n\n"
            for chunk in handle_chat_stream(
                user_id, chat_id, message,
                model=model,
                confirm_high_cost=confirm_high_cost,
                active_files=active_files,
                console_errors=console_errors,
                workspace_open=workspace_open,
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
            yield f"data: {json.dumps('__STATUS__:done')}\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/chat/title", methods=["POST"])
def api_chat_title():
    if not supabase_available():
        return jsonify({"error": "Supabase não configurado"}), 503
    try:
        data = request.get_json(silent=True) or {}
        chat_id = data.get("chat_id")
        user_id = data.get("user_id")
        first_message = (data.get("first_message") or "").strip()
        if not chat_id:
            return jsonify({"error": "chat_id obrigatório"}), 400
        if not user_id:
            return jsonify({"error": "user_id obrigatório"}), 400
        if not chat_pertence_usuario(chat_id, user_id):
            return jsonify({"error": "Chat não encontrado ou não pertence ao usuário"}), 403
        titulo = gerar_titulo_chat(first_message)
        atualizar_titulo_chat(chat_id, titulo, user_id)
        return jsonify({"titulo": titulo})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/chat/delete", methods=["POST"])
def api_chat_delete():
    if not supabase_available():
        return jsonify({"error": "Supabase não configurado"}), 503
    try:
        data = request.get_json(silent=True) or {}
        chat_id = data.get("chat_id")
        user_id = data.get("user_id")
        if not chat_id or not user_id:
            return jsonify({"error": "chat_id e user_id obrigatórios"}), 400
        if not chat_pertence_usuario(chat_id, user_id):
            return jsonify({"error": "Chat não encontrado ou não pertence ao usuário"}), 403
        if deletar_chat(chat_id, user_id):
            return jsonify({"success": True})
        return jsonify({"error": "Falha ao excluir"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/message/edit", methods=["POST"])
def api_message_edit():
    if not supabase_available():
        return jsonify({"error": "Supabase não configurado"}), 503
    try:
        data = request.get_json(silent=True) or {}
        message_id = data.get("message_id")
        user_id = data.get("user_id")
        action = (data.get("action") or "edit").strip()
        new_content = (data.get("new_content") or "").strip()
        if not message_id:
            return jsonify({"error": "message_id obrigatório"}), 400
        if not user_id:
            return jsonify({"error": "user_id obrigatório"}), 400
        if not mensagem_pertence_usuario(message_id, user_id):
            return jsonify({"error": "Mensagem não encontrada ou não pertence ao usuário"}), 403

        msg = obter_mensagem_para_edicao(message_id, user_id)
        if not msg:
            return jsonify({"error": "Mensagem não encontrada"}), 404

        if action == "improve":
            base_text = msg.get("content") or ""
            if not base_text.strip():
                return jsonify({"error": "Mensagem vazia para melhorar"}), 400
            prompt = (
                "Melhore a clareza, organização e qualidade da resposta abaixo, "
                "mantendo o mesmo significado geral. Se houver código, mantenha a mesma funcionalidade.\n\n"
                + base_text
            )
            new_content, api_key_missing = improve_message(prompt)
            if api_key_missing:
                return jsonify({"error": "OPENAI_API_KEY não configurada no servidor."}), 503
        elif not new_content:
            return jsonify({"error": "new_content obrigatório para ação 'edit'"}), 400

        if atualizar_mensagem(message_id, new_content, user_id):
            return jsonify({"content": new_content})
        return jsonify({"error": "Falha ao atualizar"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/message/delete", methods=["POST"])
def api_message_delete():
    if not supabase_available():
        return jsonify({"error": "Supabase não configurado"}), 503
    try:
        data = request.get_json(silent=True) or {}
        message_id = data.get("message_id")
        user_id = data.get("user_id")
        if not message_id:
            return jsonify({"error": "message_id obrigatório"}), 400
        if not user_id:
            return jsonify({"error": "user_id obrigatório"}), 400
        if not mensagem_pertence_usuario(message_id, user_id):
            return jsonify({"error": "Mensagem não encontrada ou não pertence ao usuário"}), 403
        if remover_mensagem(message_id, user_id):
            return jsonify({"success": True})
        return jsonify({"error": "Falha ao excluir"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
