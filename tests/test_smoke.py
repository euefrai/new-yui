"""
Smoke tests: importação e funções básicas sem chamar APIs externas.
Execute: python -m pytest tests/test_smoke.py -v
Ou: python tests/test_smoke.py
"""
import sys
from pathlib import Path

# Garante raiz do projeto no path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_config():
    from config import settings
    assert hasattr(settings, "BASE_DIR")
    assert hasattr(settings, "SUPABASE_URL")
    assert hasattr(settings, "OPENAI_API_KEY")


def test_supabase_client():
    from core.supabase_client import get_supabase_client
    get_supabase_client("anon")
    get_supabase_client("service")


def test_router():
    from yui_ai.agent.router import detect_intent
    assert detect_intent("cria um codigo de calculadora") == "chat"
    assert detect_intent("analise este codigo") == "code_analysis"
    assert detect_intent("upload de arquivo") == "upload"


def test_memory_service():
    from yui_ai.services.memory_service import load_history, save_message
    # Só testa que a interface existe; não persiste em teste real
    load_history("chat-fake", "user-fake")
    save_message("chat-fake", "user", "test", "user-fake")


def test_chat_service():
    from services.chat_service import listar_chats, supabase_available
    listar_chats("user-fake")
    supabase_available()


def test_tools_registry():
    from core.tools_registry import list_tools, get_tool
    tools = list_tools()
    assert len(tools) >= 1
    t = get_tool("listar_arquivos")
    assert t is None or isinstance(t, dict)


def test_tool_runner():
    from core.tool_runner import run_tool
    r = run_tool("listar_arquivos", {"pasta": ".", "limite": 1})
    assert "ok" in r
    assert r.get("ok") is True or "error" in r


def test_agent_controller_import():
    from backend.ai.agent_controller import _format_tool_reply
    msg = _format_tool_reply("listar_arquivos", {}, {"arquivos": ["a"], "ok": True})
    assert "a" in msg or "Arquivos" in msg


def test_tool_router():
    from backend.ai.tool_router import processar_resposta_ai
    out = processar_resposta_ai("Texto sem JSON.")
    assert out == "Texto sem JSON."


if __name__ == "__main__":
    import subprocess
    sys.exit(subprocess.run([sys.executable, "-m", "pytest", __file__, "-v"], cwd=str(ROOT)).returncode)
