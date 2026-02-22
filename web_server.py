"""
YUI Web Server — ponto de entrada enxuto.

Rotas em: routes/routes_chat.py, routes_auth.py, routes_api.py (blueprints).
Lógica em: services/, config/settings.py.
"""

import logging
import os

from flask import Flask
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from config import settings
from web.routes import register_routes
from web.routes.routes_terminal import sock, register_terminal_sock

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates",
)
app.secret_key = settings.SECRET_KEY
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
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

# Runtime mode (aplica também em Gunicorn/import time)
def _is_cloud_runtime() -> bool:
    return (
        os.environ.get("RENDER") == "true"
        or bool(os.environ.get("ZEABUR_PROJECT_ID"))
        or bool(os.environ.get("ZEABUR_SERVICE_ID"))
        or os.environ.get("TENCENT_CLOUD") == "true"
        or os.environ.get("YUI_LITE_MODE", "").lower() in ("1", "true", "yes")
    )


IS_CLOUD_RUNTIME = _is_cloud_runtime()
if IS_CLOUD_RUNTIME:
    try:
        from core.capabilities import apply_mode
        apply_mode("lite")
    except Exception as e:
        logging.warning("apply_mode(lite): %s", e)

# Event Bus: wiring (workspace_toggled → system_state etc.)
try:
    from core.event_wiring import wire_events
    wire_events()
except Exception as e:
    logging.warning("Event wiring: %s", e)

# Observability: auto-trace de eventos (Graph, Scheduler, Governor)
try:
    from core.observability import wire_observability
    wire_observability()
except Exception as e:
    logging.warning("Observability wiring: %s", e)

# Core Engine: injeta plugins no startup
try:
    from core.plugins_loader import inject_into_engine
    _tools = inject_into_engine()
    if _tools:
        logging.info("Core Engine: %d tools disponíveis (incl. plugins)", len(_tools))
except Exception as e:
    logging.warning("Plugin loader: %s", e)

# Capability Loader: escaneia capabilities/ e registra no Task Engine
try:
    from core.task_engine import get_task_engine
    from core.capability_loader import list_loaded
    get_task_engine()  # dispara carregamento
    caps = list_loaded()
    if caps:
        logging.info("Capabilities carregadas: %s", caps)
    else:
        logging.info("Capabilities: fallback bootstrap")
except Exception as e:
    logging.warning("Capability loader: %s", e)


if __name__ == "__main__":
    import threading

    def _indexar_memoria():
        # Na cloud (memória limitada), pula indexação ChromaDB para evitar OOM
        if IS_CLOUD_RUNTIME:
            return
        try:
            from core.event_bus import emit
            emit("memory_update_requested", root=str(settings.BASE_DIR))
        except Exception as e:
            logging.warning("Indexação da memória vetorial ignorada: %s", e)

    threading.Thread(target=_indexar_memoria, daemon=True).start()
    _debug = settings.FLASK_DEBUG and not IS_CLOUD_RUNTIME
    app.run(host="0.0.0.0", port=settings.PORT, debug=_debug)
