import os

from flask import Flask, jsonify, request, send_from_directory

from yui_ai.main import processar_texto_web


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")

app = Flask(
    __name__,
    static_folder=WEB_DIR,
    template_folder=WEB_DIR,
)


@app.get("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.get("/web/<path:path>")
def static_files(path: str):
    return send_from_directory(WEB_DIR, path)


@app.post("/api/chat")
def api_chat():
    data = request.get_json(silent=True) or {}
    mensagem = str(data.get("message", "") or "").strip()

    if not mensagem:
        return jsonify({"error": "Mensagem vazia."}), 400

    resposta = processar_texto_web(mensagem)
    return jsonify({"reply": resposta})


if __name__ == "__main__":
    # Exemplo simples: desenvolvimento local
    app.run(host="127.0.0.1", port=5000, debug=True)

