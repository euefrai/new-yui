"""
Yui Regression Tests — Garantia de estabilidade e performance.
Cobre: API, Ferramentas de ZIP, Intent Router, Sandbox e Cache de Busca.
"""

import time
import py_compile
from pathlib import Path

from web_server import app
from core.tools_runtime import tool_criar_projeto_arquivos, tool_criar_zip_projeto
from yui_ai.services import memory_service as mem
from yui_ai.core.intent_router import decidir_rota
from config import settings
from core import job_queue


def test_legacy_routes_modules_reexport_public_api():
    """Garante que as rotas legadas continuam funcionando após a migração."""
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
    """Testa a criação de chat e persistência de mensagens."""
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
    """Garante que a remoção de mensagens inexistentes falhe graciosamente."""
    user_id = "reg-user-remove"
    chat = mem.create_chat(user_id)
    assert chat and chat.get("id")

    chat_id = chat["id"]
    mem.save_message(chat_id, "user", "olá", user_id)
    assert mem.remove_message("inexistente", user_id) is False


def test_zip_tool_fallbacks_to_latest_generated_project_when_root_missing():
    """Testa a ferramenta de ZIP com fallback de diretório."""
    project = tool_criar_projeto_arquivos(
        root_dir="reg-zip-fallback",
        files=[{"path": "main.py", "content": "print('ok')\n"}],
    )
    assert project.get("ok") is True

    zip_result = tool_criar_zip_projeto(root_dir="", zip_name="reg-zip-fallback", background=False)
    assert zip_result.get("ok") is True
    assert str(zip_result.get("zip_output") or "").endswith(".zip")


def test_intent_router_routes_factual_questions_to_web_search():
    """Testa se o roteador de intenção identifica perguntas factuais para busca web."""
    assert decidir_rota("que jogos do brasileirão vai acontecer hoje?") == "web_search"
    assert decidir_rota("quais são os jogos mais jogados de playstation?") == "web_search"


def test_sandbox_zip_endpoint_creates_downloadable_archive():
    """Garante que o endpoint de exportação do Sandbox gera um link válido de download."""
    sandbox = Path(settings.SANDBOX_DIR)
    sandbox.mkdir(parents=True, exist_ok=True)
    sample = sandbox / "regression_zip" / "hello.txt"
    sample.parent.mkdir(parents=True, exist_ok=True)
    sample.write_text("ok", encoding="utf-8")

    client = app.test_client()
    resp = client.get("/api/sandbox/zip")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload and payload.get("ok") is True
    assert str(payload.get("url") or "").startswith("/download/")

    filename = payload["url"].split("/download/", 1)[-1]
    archive = Path(settings.GENERATED_PROJECTS_DIR) / filename
    assert archive.exists()


def test_web_search_local_fallback_when_provider_fails(monkeypatch):
    """Garante que o sistema exibe erro amigável se o provedor de busca falhar."""
    def _fake_fail(_query, limite=5):
        return {"ok": False, "resultados": [], "error": "provider down"}

    monkeypatch.setattr("core.tools_runtime.tool_buscar_web", _fake_fail)

    from services.ai_service import processar_mensagem_sync

    resp = processar_mensagem_sync(
        user_id="reg-web-fallback",
        chat_id="reg-web-fallback-chat",
        message="que jogos do brasileirão vai acontecer hoje?",
        model="yui",
    )
    assert "Não consegui consultar a web" in resp


def test_job_queue_cleanup_removes_expired_entries():
    """Testa se a fila de tarefas limpa resultados antigos corretamente."""
    job_queue._results.clear()
    job_queue._results["old"] = {"status": "done", "updated_at": 1.0}
    job_queue._results["new"] = {"status": "queued", "updated_at": 9_999_999_999.0}

    removed = job_queue.cleanup_old_jobs(ttl_seconds=10)

    assert removed == 1
    assert "old" not in job_queue._results
    assert "new" in job_queue._results


def test_sandbox_execute_javascript_basic_success():
    """Testa a execução básica de código no Sandbox."""
    client = app.test_client()
    resp = client.post('/api/sandbox/execute', json={'lang': 'javascript', 'code': 'console.log(1+1)'})
    assert resp.status_code == 200
    payload = resp.get_json() or {}
    assert payload.get('ok') is True
    assert (payload.get('stdout') or '').strip() == '2'


def test_web_search_local_uses_recent_cache_when_provider_fails(monkeypatch):
    """Verifica se o cache de busca web funciona como fallback de segurança."""
    from collections import OrderedDict
    from services import ai_service

    monkeypatch.setattr(ai_service, "_WEB_CACHE", OrderedDict())

    def _ok(_query, limite=5):
        return {"ok": True, "resultados": [{"titulo": "Exemplo", "resumo": "Resumo", "link": "https://example.com"}]}

    def _fail(_query, limite=5):
        return {"ok": False, "resultados": [], "error": "provider down"}

    monkeypatch.setattr("core.tools_runtime.tool_buscar_web", _ok)
    first = ai_service.processar_mensagem_sync(
        user_id="reg-web-cache",
        chat_id="reg-web-cache-chat",
        message="que jogos do brasileirão vai acontecer hoje?",
        model="yui",
    )
    assert "Encontrei isso na web" in first

    monkeypatch.setattr("core.tools_runtime.tool_buscar_web", _fail)
    second = ai_service.processar_mensagem_sync(
        user_id="reg-web-cache",
        chat_id="reg-web-cache-chat",
        message="que jogos do brasileirão vai acontecer hoje?",
        model="yui",
    )
    assert "Resultado recente em cache" in second


def test_runtime_metrics_endpoint_returns_queue_and_executor_stats():
    """Garante que o endpoint de monitoramento está ativo e retornando dados."""
    client = app.test_client()
    resp = client.get('/api/system/runtime_metrics')
    assert resp.status_code == 200
    payload = resp.get_json() or {}
    assert "job_queue" in payload
    assert "sandbox_executor" in payload


def test_zip_tool_background_fallback_runs_without_scheduler(monkeypatch):
    """Testa ZIP em background quando o scheduler não está disponível."""
    from core import pending_downloads

    def _boom_scheduler():
        raise RuntimeError("scheduler unavailable")

    monkeypatch.setattr("core.task_scheduler.get_scheduler", _boom_scheduler, raising=True)

    project = tool_criar_projeto_arquivos(
        root_dir="reg-zip-bg-fallback",
        files=[{"path": "app.py", "content": "print('ok')\n"}],
    )
    assert project.get("ok") is True

    zip_result = tool_criar_zip_projeto(
        root_dir="reg-zip-bg-fallback",
        zip_name="reg-zip-bg-fallback",
        background=True,
    )
    assert zip_result.get("ok") is True
    assert zip_result.get("zip_pending") is True

    expected_url = zip_result.get("download_url")
    found = False
    for _ in range(20):
        urls = pending_downloads.get_recent()
        if expected_url in urls:
            found = True
            break
        time.sleep(0.1)

    assert found is True


def test_ai_service_module_has_valid_python_syntax():
    """Verifica sintaxe válida do módulo ai_service."""
    root = Path(__file__).resolve().parents[1]
    py_compile.compile(str(root / 'services' / 'ai_service.py'), doraise=True)


def test_job_queue_module_has_valid_python_syntax():
    """Verifica sintaxe válida do módulo job_queue."""
    root = Path(__file__).resolve().parents[1]
    py_compile.compile(str(root / 'core' / 'job_queue.py'), doraise=True)


def test_sandbox_runner_module_has_valid_python_syntax():
    """Verifica sintaxe válida do módulo sandbox runner."""
    root = Path(__file__).resolve().parents[1]
    py_compile.compile(str(root / 'core' / 'sandbox_executor' / 'runner.py'), doraise=True)
