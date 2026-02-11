# Rotas em blueprints: chat, auth/main, file, user, tool.

from flask import Flask


def register_routes(app: Flask) -> None:
    """Registra todos os blueprints no app."""
    from routes.main_routes import main_bp
    from routes.chat_routes import chat_bp
    from routes.file_routes import file_bp
    from routes.user_routes import user_bp
    from routes.tool_routes import tool_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(chat_bp, url_prefix="/api")
    app.register_blueprint(file_bp, url_prefix="/api")
    app.register_blueprint(user_bp, url_prefix="/api/user")
    app.register_blueprint(tool_bp, url_prefix="/api/tools")
