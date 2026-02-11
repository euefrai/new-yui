"""
YUI Web Server — ponto de entrada enxuto.

Rotas em: routes/routes_chat.py, routes_auth.py, routes_api.py (blueprints).
Lógica em: services/, config/settings.py.
"""

from flask import Flask
from flask_cors import CORS

from config import settings
from web.routes import register_routes

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates",
)
app.secret_key = settings.SECRET_KEY
CORS(app)


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


register_routes(app)


if __name__ == "__main__":
    import os
    import threading

    # Modo LITE no Render (menos RAM, sem planner/vector/auto_debug)
    if os.environ.get("RENDER") == "true":
        from core.capabilities import apply_mode
        apply_mode("lite")

    def _indexar_memoria():
        # No Render (memória limitada), pula indexação ChromaDB para evitar OOM
        if os.environ.get("RENDER") == "true":
            return
        try:
            from backend.ai.vector_memory import indexar_projeto
            qtd = indexar_projeto(str(settings.BASE_DIR))
            print(f"🧠 Memória do projeto: {qtd} blocos indexados (yui_vector_db).")
        except Exception as e:
            print(f"⚠️ Indexação da memória vetorial ignorada: {e}")

    threading.Thread(target=_indexar_memoria, daemon=True).start()
    app.run(host="0.0.0.0", port=settings.PORT, debug=settings.FLASK_DEBUG)
