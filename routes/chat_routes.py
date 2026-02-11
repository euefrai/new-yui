# Rotas de chat: listar, criar, mensagens, stream, título, delete, edit message.

import json
import uuid

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
)
from services.ai_service import stream_resposta, gerar_titulo_chat, processar_mensagem_sync
from core.supabase_client import supabase
from yui_ai.main import processar_texto_web
from yui_ai.memory.session_memory import memory as session_memory
from yui_ai.agent.router import detect_intent
from yui_ai.agent.tool_executor import executor as tool_executor


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
    if not supabase:
        fake = {"id": str(uuid.uuid4()), "titulo": "Novo chat", "user_id": user_id}
        return jsonify(fake), 200
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
    if not user_id or not chat_id:
        return jsonify({"error": "user_id e chat_id obrigatórios"}), 400
    if not message:
        return jsonify({"error": "message obrigatória"}), 400
    if not chat_pertence_usuario(chat_id, user_id):
        return jsonify({"error": "Chat não encontrado ou não pertence ao usuário"}), 403
    try:
        reply = processar_mensagem_sync(user_id, chat_id, message)
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e), "reply": None}), 500


@chat_bp.route("/chat/stream", methods=["POST", "OPTIONS"])
def api_chat_stream():
    if request.method == "OPTIONS":
        return "", 204
    try:
        data = request.get_json(silent=True) or {}
        chat_id = data.get("chat_id")
        user_id = data.get("user_id")
        message = (data.get("message") or "").strip()
        if not chat_id:
            return jsonify({"error": "chat_id obrigatório"}), 400
        if not user_id:
            return jsonify({"error": "user_id obrigatório"}), 400
        if not message:
            return jsonify({"error": "message obrigatória"}), 400
        if not chat_pertence_usuario(chat_id, user_id):
            return jsonify({"error": "Chat não encontrado ou não pertence ao usuário"}), 403

        session["user_id"] = user_id
        history = session_memory.get(user_id)

        intent = detect_intent(message)
        if intent != "chat":
            tool_result = tool_executor.execute(intent, message)
            if tool_result:
                msg = tool_result.get("message") or str(tool_result)
                def tool_stream():
                    yield f"data: {json.dumps('__STATUS__:thinking')}\n\n"
                    yield f"data: {json.dumps(msg)}\n\n"
                    yield f"data: {json.dumps('__STATUS__:done')}\n\n"
                    session_memory.add(user_id, "user", message)
                    session_memory.add(user_id, "assistant", msg)
                return Response(
                    stream_with_context(tool_stream()),
                    mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
                )

        def generate():
            yield f"data: {json.dumps('__STATUS__:thinking')}\n\n"
            full_reply = []
            for chunk in stream_resposta(user_id, chat_id, message):
                full_reply.append(chunk)
                yield f"data: {json.dumps(chunk)}\n\n"
            yield f"data: {json.dumps('__STATUS__:done')}\n\n"
            reply_text = "".join(full_reply) if full_reply else ""
            session_memory.add(user_id, "user", message)
            session_memory.add(user_id, "assistant", reply_text)

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/chat/title", methods=["POST"])
def api_chat_title():
    if not supabase:
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
    if not supabase:
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
    if not supabase:
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
            resposta, _mid, api_key_missing = processar_texto_web(prompt, reply_to_id=None)
            if api_key_missing:
                return jsonify({"error": "OPENAI_API_KEY não configurada no servidor."}), 503
            new_content = (resposta or "").strip()
        elif not new_content:
            return jsonify({"error": "new_content obrigatório para ação 'edit'"}), 400

        if atualizar_mensagem(message_id, new_content, user_id):
            return jsonify({"content": new_content})
        return jsonify({"error": "Falha ao atualizar"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/message/delete", methods=["POST"])
def api_message_delete():
    if not supabase:
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
