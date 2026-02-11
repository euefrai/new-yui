"""
YUI Web Server — ponto de entrada enxuto.

Rotas e lógica estão em:
- routes/  (chat, file, user, tool, main)
- services/ (chat_service, ai_service)

Nada de lógica de negócio aqui; só app, CORS e registro de blueprints.
"""

import os
from flask import Flask
from flask_cors import CORS

from routes import register_routes

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates",
)
app.secret_key = os.environ.get("SECRET_KEY", "yui-dev-secret-change-in-production")
CORS(app)


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


register_routes(app)


if __name__ == "__main__":
    def _indexar_memoria():
        try:
            from backend.ai.vector_memory import indexar_projeto
            raiz = os.path.dirname(os.path.abspath(__file__))
            qtd = indexar_projeto(raiz)
            print(f"🧠 Memória do projeto: {qtd} blocos indexados (yui_vector_db).")
        except Exception as e:
            print(f"⚠️ Indexação da memória vetorial ignorada: {e}")

    import threading
    threading.Thread(target=_indexar_memoria, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=port, debug=debug)
