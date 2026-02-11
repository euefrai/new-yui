"""
YUI Web Server — ponto de entrada enxuto.

Rotas em: routes/routes_chat.py, routes_auth.py, routes_api.py (blueprints).
Lógica em: services/, config/settings.py.
"""

from flask import Flask
from flask_cors import CORS

from config.settings import BASE_DIR, FLASK_DEBUG, PORT, SECRET_KEY
from routes import register_routes

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates",
)
app.secret_key = SECRET_KEY
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
            qtd = indexar_projeto(str(BASE_DIR))
            print(f"🧠 Memória do projeto: {qtd} blocos indexados (yui_vector_db).")
        except Exception as e:
            print(f"⚠️ Indexação da memória vetorial ignorada: {e}")

    import threading
    threading.Thread(target=_indexar_memoria, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT, debug=FLASK_DEBUG)
