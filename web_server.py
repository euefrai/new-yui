"""
YUI Web Server — ponto de entrada enxuto.

Rotas em: routes/routes_chat.py, routes_auth.py, routes_api.py (blueprints).
Lógica em: services/, config/settings.py.
"""

from flask import Flask
from flask_cors import CORS

from config import settings
from web.routes import register_routes
from web.routes.routes_terminal import sock, register_terminal_sock

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates",
)
app.secret_key = settings.SECRET_KEY
CORS(app)
sock.init_app(app)
register_terminal_sock(app, sock)


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


register_routes(app)

# Core Engine: injeta plugins no startup
try:
    from core.plugins_loader import inject_into_engine
    _tools = inject_into_engine()
    if _tools:
        print(f"⚙️ Core Engine: {len(_tools)} tools disponíveis (incl. plugins)")
except Exception as e:
    print(f"⚠️ Plugin loader: {e}")


if __name__ == "__main__":
    import os
    import threading

    # Modo LITE em cloud (Render, Zeabur): menos RAM, sem planner/vector/auto_debug
    _is_cloud = (
        os.environ.get("RENDER") == "true"
        or os.environ.get("ZEABUR_PROJECT_ID")
        or os.environ.get("ZEABUR_SERVICE_ID")
    )
    if _is_cloud:
        from core.capabilities import apply_mode
        apply_mode("lite")

    def _indexar_memoria():
        # Na cloud (memória limitada), pula indexação ChromaDB para evitar OOM
        if _is_cloud:
            return
        try:
            from backend.ai.vector_memory import indexar_projeto
            qtd = indexar_projeto(str(settings.BASE_DIR))
            print(f"🧠 Memória do projeto: {qtd} blocos indexados (yui_vector_db).")
        except Exception as e:
            print(f"⚠️ Indexação da memória vetorial ignorada: {e}")

    threading.Thread(target=_indexar_memoria, daemon=True).start()
    _debug = settings.FLASK_DEBUG and not (
        os.environ.get("RENDER") == "true"
        or os.environ.get("ZEABUR_PROJECT_ID")
        or os.environ.get("ZEABUR_SERVICE_ID")
    )
    app.run(host="0.0.0.0", port=settings.PORT, debug=_debug)
