# Rotas em blueprints: routes_chat, routes_auth, routes_api (Flask respira melhor).

from flask import Flask


def register_routes(app: Flask) -> None:
    """Registra todos os blueprints no app."""
    from routes.routes_api import main_bp, file_bp, tool_bp
    from routes.routes_chat import chat_bp
    from routes.routes_auth import user_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(chat_bp, url_prefix="/api")
    app.register_blueprint(file_bp, url_prefix="/api")
    app.register_blueprint(user_bp, url_prefix="/api/user")
    app.register_blueprint(tool_bp, url_prefix="/api/tools")
