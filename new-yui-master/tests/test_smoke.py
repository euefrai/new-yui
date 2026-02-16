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


def test_attention_manager():
    from core.attention_manager import score, select, filter_tools_by_intention
    items = [
        {"key": "a", "priority": 1, "recent": True, "task_relevant": False},
        {"key": "b", "priority": 3, "recent": False, "task_relevant": True},
    ]
    sel = select(items, top=1)
    assert len(sel) == 1
    tools = filter_tools_by_intention(
        ["analisar_arquivo", "criar_projeto_arquivos", "consultar_indice_projeto"],
        "criar calculadora"
    )
    assert "criar_projeto_arquivos" in tools


def test_strategy_engine():
    from core.strategy_engine import StrategyEngine, get_strategy_engine
    se = StrategyEngine()
    s = se.choose(meta_signals={"loop_detected": True}, energy=100)
    assert s == "correction"
    s2 = se.choose(meta_signals={}, energy=10)
    assert s2 == "minimal"
    assert se.get_max_steps("minimal") == 1
    assert se.get_attention_top("focused") == 5


def test_world_model():
    from core.world_model import WorldModel, get_world_model
    wm = WorldModel()
    wm.update_project(known_files=["main.py", "app.py"], main_file="main.py", root=".")
    assert wm.file_exists("main.py")
    assert wm.get_focus_hint()
    wm.save()


def test_metacognition():
    from core.metacognition import MetaCognition, MetaState, get_metacognition, record_action
    meta = MetaCognition()
    state = MetaState(energy=50, context_size=10, steps_planned=5)
    signals = meta.analyze(state)
    assert "low_energy" in signals
    assert "meta_score" in signals
    assert "simplified_mode" in signals
    record_action("test_tool")
    record_action("test_tool")
    record_action("test_tool")
    signals2 = meta.analyze(MetaState(energy=50))
    assert signals2.get("loop_detected") is True


def test_identity_core():
    from core.identity_core import IdentityCore, get_identity_core
    identity = IdentityCore()
    assert identity.decision_style in ("pragmatic", "exploratory")
    assert identity.risk_tolerance in ("low", "medium", "high")
    assert identity.response_depth in ("short", "medium", "long")
    ok, _ = identity.validate("execute", tool_name="analisar_arquivo", args={})
    assert ok is True
    ok2, _ = identity.validate("execute", tool_name="deletar_arquivo", args={})
    assert ok2 is False


def test_energy_manager():
    from core.energy_manager import EnergyManager, get_energy_manager, COST_TOOL, COST_PLANNER
    em = EnergyManager()
    em.energy = 50
    em.consume(COST_TOOL)
    assert em.energy < 50
    assert em.can_execute()
    em.energy = 5
    assert em.is_low()
    assert em.is_critical()


if __name__ == "__main__":
    import subprocess
    sys.exit(subprocess.run([sys.executable, "-m", "pytest", __file__, "-v"], cwd=str(ROOT)).returncode)
