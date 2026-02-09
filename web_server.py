import os

from flask import Flask, jsonify, request, send_from_directory

from yui_ai.main import processar_texto_web
from yui_ai.analyzer.report_formatter import run_file_analysis, report_to_text


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")

app = Flask(
    __name__,
    static_folder=WEB_DIR,
    template_folder=WEB_DIR,
)


@app.after_request
def add_cors_headers(response):
    """Permite requisições do frontend mesmo quando aberto por file:// ou outro host."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/", methods=["GET", "OPTIONS"])
def index():
    if request.method == "OPTIONS":
        return "", 204
    return send_from_directory(WEB_DIR, "index.html")


@app.get("/web/<path:path>")
def static_files(path: str):
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
    """Upload de arquivo: analisa e retorna resposta em texto (fluxo chat)."""
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
    # Desenvolvimento local ou Render (usa PORT e 0.0.0.0)
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=port, debug=debug)

