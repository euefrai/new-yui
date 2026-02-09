import os
import json
import uuid

from flask import Flask, jsonify, request, send_from_directory, render_template, Response, stream_with_context
from flask_cors import CORS

from yui_ai.main import processar_texto_web
from yui_ai.analyzer.report_formatter import run_file_analysis, report_to_text
from yui_ai.core.ai_engine import stream_resposta_yui, gerar_titulo_chat

from core.supabase_client import supabase
from core.memory import create_chat as memory_create_chat, get_chats as memory_get_chats, get_messages as memory_get_messages, save_message as memory_save_message, update_chat_title as memory_update_chat_title
from core.engine import process_message as engine_process_message


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates",
)
CORS(app)


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


def _supabase_url():
    return (os.environ.get("SUPABASE_URL") or "").strip()


def _supabase_key():
    return (os.environ.get("SUPABASE_KEY") or "").strip()


def _supabase_public_key():
    """Chave pública (publishable/anon) para o frontend; nunca envie service_role ao browser."""
    return (
        (os.environ.get("SUPABASE_PUBLISHABLE_KEY") or "").strip()
        or (os.environ.get("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY") or "").strip()
    ) or _supabase_key()


# ========== App principal (login + chats por usuário) ==========
@app.route("/", methods=["GET", "OPTIONS"])
def index():
    if request.method == "OPTIONS":
        return "", 204
    return render_template(
        "index.html",
        supabase_url=_supabase_url(),
        supabase_key=_supabase_public_key(),
    )


# ========== Rotas Supabase (chats e mensagens) ==========
@app.route("/get_chats", methods=["POST"])
def get_chats():
    if not supabase:
        return jsonify([]), 200
    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id")
        if not user_id:
            return jsonify({"error": "user_id obrigatório"}), 400
        return jsonify(memory_get_chats(user_id))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/create_chat", methods=["POST"])
def create_chat():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id obrigatório"}), 400

    if not supabase:
        # Sem Supabase: retorna um chat “local” para a sessão funcionar
        fake = {"id": str(uuid.uuid4()), "titulo": "Novo chat", "user_id": user_id}
        return jsonify(fake), 200

    try:
        chat = memory_create_chat(user_id)
        if not chat:
            return jsonify({"error": "Falha ao criar chat"}), 500
        return jsonify(chat)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/get_messages", methods=["POST"])
def get_messages():
    if not supabase:
        return jsonify([]), 200
    try:
        data = request.get_json(silent=True) or {}
        chat_id = data.get("chat_id")
        if not chat_id:
            return jsonify({"error": "chat_id obrigatório"}), 400
        return jsonify(memory_get_messages(chat_id))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        return "", 204
    try:
        data = request.get_json(silent=True) or {}
        chat_id = data.get("chat_id")
        message = (data.get("message") or "").strip()
        if not chat_id:
            return jsonify({"error": "chat_id obrigatório"}), 400
        if not message:
            return jsonify({"error": "message obrigatória"}), 400

        memory_save_message(chat_id, "user", message)

        resposta, _message_id, api_key_missing = processar_texto_web(message, reply_to_id=None)
        if api_key_missing:
            resposta = "⚠️ Configure OPENAI_API_KEY no servidor para respostas da Yui."

        memory_save_message(chat_id, "assistant", resposta)

        return jsonify({"message": resposta})
    except Exception as e:
        return jsonify({"error": str(e), "message": None}), 500


@app.route("/chat/stream", methods=["POST", "OPTIONS"])
def chat_stream():
    if request.method == "OPTIONS":
        return "", 204
    try:
        data = request.get_json(silent=True) or {}
        chat_id = data.get("chat_id")
        message = (data.get("message") or "").strip()
        if not chat_id:
            return jsonify({"error": "chat_id obrigatório"}), 400
        if not message:
            return jsonify({"error": "message obrigatória"}), 400

        memory_save_message(chat_id, "user", message)

        full_content = []

        def generate():
            for chunk in stream_resposta_yui(message):
                full_content.append(chunk)
                yield f"data: {json.dumps(chunk)}\n\n"
            content = "".join(full_content)
            if content:
                try:
                    memory_save_message(chat_id, "assistant", content)
                except Exception:
                    pass

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/generate_chat_title", methods=["POST"])
def generate_chat_title():
    if not supabase:
        return jsonify({"error": "Supabase não configurado"}), 503
    try:
        data = request.get_json(silent=True) or {}
        chat_id = data.get("chat_id")
        first_message = (data.get("first_message") or "").strip()
        if not chat_id:
            return jsonify({"error": "chat_id obrigatório"}), 400
        titulo = gerar_titulo_chat(first_message)
        memory_update_chat_title(chat_id, titulo)
        return jsonify({"titulo": titulo})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========== API nova (core engine) ==========
@app.route("/api/chats/<user_id>")
def api_get_chats(user_id):
    return jsonify(memory_get_chats(user_id))


@app.route("/api/chat/new", methods=["POST"])
def api_new_chat():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id obrigatório"}), 400
    if not supabase:
        fake = {"id": str(uuid.uuid4()), "titulo": "Novo chat", "user_id": user_id}
        return jsonify(fake), 200
    chat = memory_create_chat(user_id)
    if not chat:
        return jsonify({"error": "Falha ao criar chat"}), 500
    return jsonify(chat)


@app.route("/api/messages/<chat_id>")
def api_messages(chat_id):
    return jsonify(memory_get_messages(chat_id))


@app.route("/api/send", methods=["POST"])
def api_send():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    chat_id = data.get("chat_id")
    message = (data.get("message") or "").strip()
    if not user_id or not chat_id:
        return jsonify({"error": "user_id e chat_id obrigatórios"}), 400
    if not message:
        return jsonify({"error": "message obrigatória"}), 400
    try:
        reply = engine_process_message(user_id, chat_id, message)
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e), "reply": None}), 500


# ========== API legada (compatibilidade) ==========
@app.get("/web/<path:path>")
def web_static(path: str):
    return send_from_directory(WEB_DIR, path)


@app.route("/api/chat", methods=["POST", "OPTIONS"])
def api_chat():
    if request.method == "OPTIONS":
        return "", 204
    try:
        data = request.get_json(silent=True) or {}
        mensagem = str(data.get("message", "") or "").strip()
        reply_to = data.get("reply_to")
        if not mensagem:
            return jsonify({"error": "Mensagem vazia."}), 400
        resposta, message_id, api_key_missing = processar_texto_web(mensagem, reply_to_id=reply_to)
        return jsonify({"reply": resposta, "message_id": message_id, "api_key_missing": api_key_missing})
    except Exception as e:
        return jsonify({"error": "Erro no servidor: " + str(e), "reply": None}), 500


@app.post("/api/analyze-file")
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
    ok, report, err = run_file_analysis(content, f.filename)
    if not ok:
        return jsonify({"success": False, "error": err}), 400
    return jsonify({"success": True, "report": report})


@app.route("/upload", methods=["POST", "OPTIONS"])
def upload():
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
        ok, report, err = run_file_analysis(content, f.filename)
        if not ok:
            return jsonify({"error": err or "Erro na análise."}), 400
        text = report_to_text(report)
        return jsonify({"response": text})
    except Exception as e:
        return jsonify({"error": "Erro no servidor: " + str(e), "response": None}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=port, debug=debug)
