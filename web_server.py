import os
import json
import uuid

from flask import Flask, jsonify, request, send_from_directory, render_template, Response, stream_with_context
from flask_cors import CORS

from yui_ai.main import processar_texto_web
from yui_ai.analyzer.report_formatter import run_file_analysis, report_to_text
from yui_ai.core.ai_engine import stream_resposta_yui, gerar_titulo_chat

from core.supabase_client import supabase
from core.memory import (
    create_chat as memory_create_chat,
    get_chats as memory_get_chats,
    get_messages as memory_get_messages,
    save_message as memory_save_message,
    update_chat_title as memory_update_chat_title,
)
from core.engine import process_message as engine_process_message
from core.tools_registry import list_tools
from core.tool_runner import run_tool
from core.user_profile import get_user_profile, upsert_user_profile


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
GENERATED_DIR = os.path.join(BASE_DIR, "generated_projects")

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


# ========== API chat unificada (/api/chats, /api/chat/*, /api/messages, /api/send, etc.) ==========
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


@app.route("/api/chat/stream", methods=["POST", "OPTIONS"])
def api_chat_stream():
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

        msg_lower = message.lower()
        if "```" in message or "analis" in msg_lower or "código" in msg_lower or "codigo" in msg_lower:
            initial_state = "analyzing_code"
        else:
            initial_state = "thinking"

        full_content = []

        def generate():
            yield f"data: {json.dumps('__STATUS__:' + initial_state)}\n\n"
            for chunk in stream_resposta_yui(message):
                full_content.append(chunk)
                yield f"data: {json.dumps(chunk)}\n\n"
            content = "".join(full_content)
            if content:
                try:
                    memory_save_message(chat_id, "assistant", content)
                except Exception:
                    pass
            yield f"data: {json.dumps('__STATUS__:done')}\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat/title", methods=["POST"])
def api_chat_title():
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


@app.route("/api/chat/delete", methods=["POST"])
def api_chat_delete():
    if not supabase:
        return jsonify({"error": "Supabase não configurado"}), 503
    try:
        data = request.get_json(silent=True) or {}
        chat_id = data.get("chat_id")
        user_id = data.get("user_id")
        if not chat_id or not user_id:
            return jsonify({"error": "chat_id e user_id obrigatórios"}), 400
        supabase.table("chats").delete().eq("id", chat_id).eq("user_id", user_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/message/edit", methods=["POST"])
def api_message_edit():
    if not supabase:
        return jsonify({"error": "Supabase não configurado"}), 503
    try:
        data = request.get_json(silent=True) or {}
        message_id = data.get("message_id")
        action = (data.get("action") or "edit").strip()
        new_content = (data.get("new_content") or "").strip()
        if not message_id:
            return jsonify({"error": "message_id obrigatório"}), 400

        res = supabase.table("messages").select("*").eq("id", message_id).limit(1).execute()
        if not res.data:
            return jsonify({"error": "Mensagem não encontrada"}), 404
        msg = res.data[0]

        if action == "improve":
            base_text = msg.get("content") or ""
            if not base_text.strip():
                return jsonify({"error": "Mensagem vazia para melhorar"}), 400
            prompt = (
                "Melhore a clareza, organização e qualidade da resposta abaixo, "
                "mantendo o mesmo significado geral. Se houver código, mantenha a mesma funcionalidade.\n\n"
                + base_text
            )
            resposta, _message_id, api_key_missing = processar_texto_web(prompt, reply_to_id=None)
            if api_key_missing:
                return jsonify({"error": "OPENAI_API_KEY não configurada no servidor."}), 503
            new_content = (resposta or "").strip()
        elif not new_content:
            return jsonify({"error": "new_content obrigatório para ação 'edit'"}), 400

        supabase.table("messages").update({"content": new_content}).eq("id", message_id).execute()
        return jsonify({"content": new_content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/message/delete", methods=["POST"])
def api_message_delete():
    if not supabase:
        return jsonify({"error": "Supabase não configurado"}), 503
    try:
        data = request.get_json(silent=True) or {}
        message_id = data.get("message_id")
        if not message_id:
            return jsonify({"error": "message_id obrigatório"}), 400
        supabase.table("messages").delete().eq("id", message_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/upload", methods=["POST", "OPTIONS"])
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


@app.route("/api/user/profile", methods=["POST"])
def api_user_profile():
    """
    Cria/atualiza o perfil do usuário com preferências básicas.

    Body:
    {
      "user_id": "...",        # obrigatório
      "email": "...",          # opcional
      "nivel_tecnico": "...",  # opcional
      "linguagens_pref": "...",
      "modo_resposta": "dev|explicativo|resumido"
    }
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


@app.route("/api/user/profile/get", methods=["POST"])
def api_user_profile_get():
    """Retorna o perfil de usuário armazenado (ou defaults)."""
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "user_id obrigatório"}), 400
    profile = get_user_profile(user_id)
    return jsonify({"success": True, "profile": profile})


@app.route("/api/tools", methods=["GET"])
def api_list_tools():
    """Lista ferramentas disponíveis para uso pela Yui / cliente."""
    return jsonify(list_tools())


@app.route("/api/tools/run", methods=["POST"])
def api_run_tool():
    """
    Executa uma ferramenta registrada.

    Body esperado:
    {
      "name": "analisar_arquivo",
      "args": { ... }
    }
    """
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    args = data.get("args") or {}
    if not name:
        return jsonify({"ok": False, "result": None, "error": "name obrigatório"}), 400
    result = run_tool(name, args)
    status = 200 if result.get("ok") else 400
    return jsonify(result), status


# ========== API legada (compatibilidade) ==========
@app.get("/web/<path:path>")
def web_static(path: str):
    return send_from_directory(WEB_DIR, path)


@app.route("/generated/<path:path>")
def generated_static(path: str):
    """Serve arquivos dos projetos gerados automaticamente (preview)."""
    return send_from_directory(GENERATED_DIR, path)


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
    # Usa a ferramenta padronizada (tool_analisar_arquivo)
    from core.tool_runner import run_tool

    result = run_tool(
        "analisar_arquivo",
        {"filename": f.filename, "content": content.decode("utf-8", errors="ignore")},
    )
    if not result.get("ok"):
        return jsonify({"success": False, "error": result.get("error")}), 400
    # Mantém compatibilidade: retorna o report bruto da ferramenta, se existir
    report = (result.get("result") or {}).get("report")
    if not report:
        return jsonify({"success": False, "error": "Relatório vazio."}), 400
    return jsonify({"success": True, "report": report})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=port, debug=debug)
