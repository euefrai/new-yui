# Blueprints: chat, auth, api (main + file + tool).
# web_server registra estes blueprints; nenhuma lógica de negócio aqui.

from flask import Flask


def register_routes(app: Flask) -> None:
    """Registra todos os blueprints no app."""
    from web.routes.routes_api import main_bp, file_bp, tool_bp, goals_bp, missions_bp, system_bp, sandbox_bp
    from web.routes.routes_chat import chat_bp
    from web.routes.routes_auth import user_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(chat_bp, url_prefix="/api")
    app.register_blueprint(file_bp, url_prefix="/api")
    app.register_blueprint(user_bp, url_prefix="/api/user")
    app.register_blueprint(tool_bp, url_prefix="/api/tools")
    app.register_blueprint(system_bp)
    app.register_blueprint(sandbox_bp)
    app.register_blueprint(goals_bp)
    app.register_blueprint(missions_bp)