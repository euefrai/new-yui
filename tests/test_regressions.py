from web_server import app
from yui_ai.services import memory_service as mem


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
