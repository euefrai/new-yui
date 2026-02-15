from web_server import app
from core.tools_runtime import tool_criar_projeto_arquivos, tool_criar_zip_projeto
from yui_ai.services import memory_service as mem
from yui_ai.core.intent_router import decidir_rota


def test_legacy_routes_modules_reexport_public_api():
    # Import legado deve continuar funcionando para funções e blueprints.
    from routes.routes_api import clear_chat, main_bp
    from routes.routes_chat import api_new_chat, chat_bp
    from routes.routes_auth import api_user_profile, user_bp

    assert callable(clear_chat)
    assert callable(api_new_chat)
    assert callable(api_user_profile)
    assert main_bp.name == "main"
    assert chat_bp.name == "chat"
    assert user_bp.name == "user"


def test_api_new_chat_persists_local_chat():
    client = app.test_client()
    user_id = "reg-user-local"

    resp = client.post("/api/chat/new", json={"user_id": user_id})
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload and payload.get("id")

    chat_id = payload["id"]
    messages_resp = client.get(f"/api/messages/{chat_id}?user_id={user_id}")
    assert messages_resp.status_code == 200
    assert isinstance(messages_resp.get_json(), list)


def test_remove_message_returns_false_when_message_missing():
    user_id = "reg-user-remove"
    chat = mem.create_chat(user_id)
    assert chat and chat.get("id")

    chat_id = chat["id"]
    mem.save_message(chat_id, "user", "olá", user_id)
    assert mem.remove_message("inexistente", user_id) is False


def test_zip_tool_fallbacks_to_latest_generated_project_when_root_missing():
    project = tool_criar_projeto_arquivos(
        root_dir="reg-zip-fallback",
        files=[{"path": "main.py", "content": "print('ok')\n"}],
    )
    assert project.get("ok") is True

    zip_result = tool_criar_zip_projeto(root_dir="", zip_name="reg-zip-fallback", background=False)
    assert zip_result.get("ok") is True
    assert str(zip_result.get("zip_output") or "").endswith(".zip")


def test_intent_router_routes_factual_questions_to_web_search():
    assert decidir_rota("que jogos do brasileirão vai acontecer hoje?") == "web_search"
    assert decidir_rota("quais são os jogos mais jogados de playstation?") == "web_search"
