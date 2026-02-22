# Rotas de API: index, estáticos, download, clear_chat, upload, analyze, tools.

from pathlib import Path
import zipfile
from datetime import datetime

from flask import Blueprint, request, render_template, send_from_directory, jsonify, session

from config import settings
from core.tool_runner import run_tool
from core.tools_registry import list_tools


# --- Main (index, estáticos, download, clear_chat) ---
main_bp = Blueprint("main", __name__)


@main_bp.route("/", methods=["GET", "OPTIONS"])
def index():
    if request.method == "OPTIONS":
        return "", 204
    return render_template(
        "index.html",
        supabase_url=settings.SUPABASE_URL or "",
        supabase_key=settings.SUPABASE_ANON_KEY or "",
        use_minified=settings.USE_MINIFIED_STATIC,
        static_version=settings.STATIC_VERSION,
    )


@main_bp.get("/web/<path:path>")
def web_static(path: str):
    return send_from_directory(str(settings.WEB_LEGACY_DIR), path)


@main_bp.route("/generated/<path:path>")
def generated_static(path: str):
    return send_from_directory(str(settings.GENERATED_PROJECTS_DIR), path)


@main_bp.route("/download/<path:filename>")
def download_file(filename: str):
    """Serve arquivos de generated_projects para download (ex.: .zip do projeto)."""
    return send_from_directory(str(settings.GENERATED_PROJECTS_DIR), filename, as_attachment=True)


@main_bp.route("/clear_chat", methods=["POST"])
def clear_chat():
    user_id = session.get("user_id")
    if not user_id:
        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id obrigatório", "status": "error"}), 400
    try:
        from yui_ai.memory.session_memory import memory
        memory.clear(user_id)
        from core.session_manager import clear_session
        clear_session(user_id)
        try:
            from core.context_engine import clear_session as clear_operational_context
            clear_operational_context(user_id)
        except Exception:
            pass
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# --- File (upload, analyze) ---
file_bp = Blueprint("file", __name__, url_prefix="")


@file_bp.route("/upload", methods=["POST", "OPTIONS"])
def api_upload():
    if request.method == "OPTIONS":
        return "", 204
    try:
        if "file" not in request.files:
            return jsonify({"error": "Nenhum arquivo enviado."}), 400
        f = request.files["file"]
        if not f or not f.filename:
            return jsonify({"error": "Arquivo inválido."}), 400
        try:
            content = f.read()
        except Exception as e:
            return jsonify({"error": str(e)}), 400

        result = run_tool(
            "analisar_arquivo",
            {"filename": f.filename, "content": content.decode("utf-8", errors="ignore")},
        )
        if not result.get("ok"):
            return jsonify({"error": result.get("error") or "Erro na análise."}), 400
        text = (result.get("result") or {}).get("text") or ""
        if not text:
            return jsonify({"error": "Relatório vazio."}), 400
        return jsonify({"response": text})
    except Exception as e:
        return jsonify({"error": str(e), "response": None}), 500


@file_bp.post("/analyze-file")
def api_analyze_file():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "Nenhum arquivo enviado."}), 400
    f = request.files["file"]
    if not f or not f.filename:
        return jsonify({"success": False, "error": "Arquivo inválido."}), 400
    try:
        content = f.read()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400
    result = run_tool(
        "analisar_arquivo",
        {"filename": f.filename, "content": content.decode("utf-8", errors="ignore")},
    )
    if not result.get("ok"):
        return jsonify({"success": False, "error": result.get("error")}), 400
    report = (result.get("result") or {}).get("report")
    if not report:
        return jsonify({"success": False, "error": "Relatório vazio."}), 400
    return jsonify({"success": True, "report": report})


# --- Tool (listar, executar) ---
tool_bp = Blueprint("tool", __name__, url_prefix="")


@tool_bp.route("", methods=["GET"])
@tool_bp.route("/", methods=["GET"])
def api_list_tools():
    return jsonify(list_tools())


@tool_bp.route("/run", methods=["POST"])
def api_run_tool():
    """
    Body: name (obrigatório), args (dict).
    """
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    args = data.get("args") or {}
    if not name:
        return jsonify({"ok": False, "result": None, "error": "name obrigatório"}), 400
    result = run_tool(name, args)
    status = 200 if result.get("ok") else 400
    return jsonify(result), status


# --- System (saúde, telemetria) ---
system_bp = Blueprint("system", __name__, url_prefix="/api/system")


@system_bp.get("/health")
def api_system_health():
    """
    Saúde do servidor: CPU, RAM, modo (normal/fast/critical).
    Alimenta o painel de Saúde do Sistema na UI.
    """
    try:
        from core.self_monitoring import get_system_snapshot
        snap = get_system_snapshot(use_cache=True)
        if snap:
            data = snap.to_dict()
            data["available"] = True
        else:
            data = {"available": False, "message": "Monitoramento não disponível (psutil)"}
    except Exception as e:
        data = {"available": False, "error": str(e)}
    return jsonify(data)


@system_bp.get("/telemetry")
def api_system_telemetry():
    """
    Custo acumulado do dia (baseado em energia consumida).
    Transparência para o usuário do SaaS.
    """
    try:
        from core.usage_tracker import get_today_usage
        try:
            from core.energy_manager import get_energy_manager
            energy = get_energy_manager().energy
        except Exception:
            energy = 100
        usage = get_today_usage()
        usage["energy_current"] = energy
        return jsonify(usage)
    except Exception as e:
        return jsonify({"error": str(e), "energy_consumed": 0, "requests": 0, "cost_estimate": 0})




@system_bp.get("/runtime_metrics")
def api_system_runtime_metrics():
    """Métricas leves de runtime (fila assíncrona + executor sandbox)."""
    try:
        from core.job_queue import get_job_metrics
    except Exception:
        def get_job_metrics():
            return {"available": False}
    try:
        from core.sandbox_executor.runner import get_execution_metrics
    except Exception:
        def get_execution_metrics():
            return {"available": False}
    return jsonify({
        "job_queue": get_job_metrics(),
        "sandbox_executor": get_execution_metrics(),
    })

@system_bp.post("/cleanup")
def api_system_cleanup():
    """
    Limpeza: generated_projects + arquivos temporários do sandbox.
    Também encerra terminais sem interação há > 2 min (kill switch).
    Chamar periodicamente (ex: cron) para reduzir carga no Zeabur.
    """
    import shutil
    try:
        from web.routes.routes_terminal import cleanup_processes
        cleanup_processes()
    except Exception:
        pass
    try:
        from config import settings
        deleted = 0
        gen_dir = Path(settings.GENERATED_PROJECTS_DIR)
        if gen_dir.is_dir():
            for child in gen_dir.iterdir():
                try:
                    if child.is_dir():
                        shutil.rmtree(child)
                    else:
                        child.unlink()
                    deleted += 1
                except Exception:
                    pass
        sandbox = Path(settings.SANDBOX_DIR)
        for name in ("_run_script.py", "_run_script.js"):
            p = sandbox / name
            if p.exists():
                try:
                    p.unlink()
                    deleted += 1
                except Exception:
                    pass
        return jsonify({"ok": True, "deleted": deleted})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@system_bp.post("/events")
def api_system_events():
    """
    Frontend emite eventos no Event Bus.
    Body: { event: str, data?: dict }
    Ex: { "event": "workspace_toggled", "data": { "open": true } }
    """
    data = request.get_json(silent=True) or {}
    evt = (data.get("event") or "").strip()
    payload = data.get("data") or data
    if not evt:
        return jsonify({"ok": False, "error": "event obrigatório"}), 400
    allow = {"workspace_toggled", "file_changed", "preview_started"}
    if evt not in allow:
        return jsonify({"ok": False, "error": f"evento não permitido: {evt}"}), 400
    try:
        from core.event_bus import emit
        if isinstance(payload, dict):
            emit(evt, **payload)
        else:
            emit(evt, payload)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@system_bp.get("/guard")
def api_system_guard():
    """
    Execution Guard — status de recursos (RAM, CPU) antes de executar tarefas.
    """
    try:
        from core.execution_guard import get_guard
        d = get_guard().pode_executar()
        return jsonify({
            "ok": True,
            "can_execute": d.ok,
            "reason": d.reason,
            "ram_used_mb": round(d.ram_used_mb, 1),
            "ram_limit_mb": d.ram_limit_mb,
            "cpu_percent": round(d.cpu_percent, 1),
            "cpu_limit": d.cpu_limit,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "can_execute": True}), 500


@system_bp.get("/governor")
def api_system_governor():
    """
    Resource Governor — decisões permitir/bloquear por feature.
    Frontend pode consultar para decidir (ex: enable preview só se allow_preview).
    """
    try:
        from core.resource_governor import allow_preview, allow_planner, allow_heavy_agent, allow_watchers
        ram, cpu = 0.0, 0.0
        try:
            from core.self_monitoring import get_system_snapshot
            snap = get_system_snapshot(use_cache=True)
            if snap:
                ram, cpu = snap.ram_percent, snap.cpu_percent
        except Exception:
            pass
        d_preview = allow_preview(ram)
        d_planner = allow_planner(cpu)
        d_heavy = allow_heavy_agent(cpu_usage=cpu, ram_usage=ram)
        d_watchers = allow_watchers(ram)
        return jsonify({
            "ok": True,
            "ram": round(ram, 1),
            "cpu": round(cpu, 1),
            "allow_preview": d_preview.allow,
            "allow_planner": d_planner.allow,
            "allow_heavy_agent": d_heavy.allow,
            "allow_watchers": d_watchers.allow,
            "reasons": {
                "preview": d_preview.reason,
                "planner": d_planner.reason,
                "heavy_agent": d_heavy.reason,
                "watchers": d_watchers.reason,
            },
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@system_bp.get("/scheduler")
def api_system_scheduler():
    """
    Task Scheduler — status da fila de tarefas em background.
    """
    try:
        from core.task_scheduler import get_scheduler
        s = get_scheduler()
        return jsonify({"ok": True, "queue_size": s.queue_size()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@system_bp.get("/observability")
def api_system_observability():
    """
    Observability Layer — timeline de execução e System Activity.
    timeline: spans com duração (ms)
    activity: eventos recentes (graph, task, governor, event)
    """
    try:
        from core.observability import get_observability_snapshot
        snap = get_observability_snapshot()
        return jsonify({"ok": True, **snap})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "timeline": [], "activity": []}), 500


@system_bp.post("/autodev")
def api_system_autodev():
    """
    AutoDev Agent — agente autônomo com controle do workspace.
    Body: { message, dry_run?, auto_approve? }
    - dry_run: simula execução sem alterar arquivos
    - auto_approve: executa tools sem confirmação (default true)
    """
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or data.get("msg") or "").strip()
    if not message:
        return jsonify({"ok": False, "error": "message obrigatória"}), 400
    dry_run = data.get("dry_run", False)
    auto_approve = data.get("auto_approve", True)
    try:
        from core.autodev_agent import run_autodev
        chunks = list(run_autodev(message, dry_run=dry_run, auto_approve=auto_approve))
        reply = "".join(chunks)
        return jsonify({"ok": True, "reply": reply, "dry_run": dry_run})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@system_bp.get("/skills")
def api_system_skills():
    """
    Skill Registry — skills ativas (auto-descoberta de capacidades).
    UI pode mostrar: ✔ code-edit, ✔ terminal-exec, etc.
    """
    try:
        from core.skills.registry import list_skills
        skills = list_skills()
        return jsonify({"ok": True, "skills": skills})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "skills": []}), 500


@system_bp.get("/workspace_index")
def api_system_workspace_index():
    """
    Workspace Indexer — mapa mental do projeto (snapshot leve).
    """
    try:
        from core.workspace_indexer import scan
        base = request.args.get("base")
        mapa = scan(base)
        return jsonify({"ok": True, "mapa": mapa})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "mapa": {}}), 500


@system_bp.get("/capabilities")
def api_system_capabilities():
    """
    Capability Loader — capabilities carregadas dinamicamente.
    """
    try:
        from core.capability_loader import list_loaded
        caps = list_loaded()
        return jsonify({"ok": True, "capabilities": caps})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "capabilities": []}), 500


@system_bp.get("/tasks/active")
def api_system_tasks_active():
    """
    Task Engine — tarefas em execução e resumo para UI.
    Ex: active_count=2, summary_text="editando 2 arquivos, gerando ZIP"
    UI pode mostrar: 🟡 Heathcliff está editando 3 arquivos...
    """
    try:
        from core.task_engine import get_task_engine
        engine = get_task_engine()
        summary = engine.get_summary()
        return jsonify({"ok": True, **summary})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "active_count": 0, "active": [], "summary_text": ""}), 500


@system_bp.get("/pending_downloads")
def api_system_pending_downloads():
    """
    URLs de downloads prontos (ex: ZIP gerado em background).
    Query: since (opcional) — timestamp para retornar só os novos.
    """
    try:
        from core.pending_downloads import get_recent
        since = request.args.get("since", type=float)
        urls = get_recent(since=since)
        return jsonify({"ok": True, "urls": urls})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "urls": []}), 500


@system_bp.get("/state")
def api_system_state():
    """
    System State — estado global para consistência operacional.
    mode, workspace_open, executing_graph, terminal_sessions_alive.
    """
    try:
        from core.system_state import get_state
        return jsonify({"ok": True, "state": get_state().to_dict()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@system_bp.get("/execution")
def api_system_execution():
    """
    Execution Graph — status dos nós para UI de progresso.
    Retorna [{"name": "Planner", "status": "done", "symbol": "✓"}, ...]
    Quando agent_controller usar ExecutionGraph, define via set_execution_graph().
    """
    try:
        from core.agent_context import get_execution_graph
        graph = get_execution_graph()
        if graph and hasattr(graph, "to_ui_status"):
            return jsonify({"ok": True, "nodes": graph.to_ui_status(), "intention": getattr(graph, "intention", "")})
        return jsonify({"ok": True, "nodes": [], "intention": ""})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "nodes": []}), 500


@system_bp.get("/cognitive")
def api_system_cognitive():
    """
    Cognitive Status — Observability do Cognitive Loop.
    Planner confidence, last action score, RAM impact.
    """
    try:
        from core.cognitive import get_cognitive_status
        from core.cognitive.observer import get_last_observation
        from core.self_state import get as get_self_state
        status = get_cognitive_status()
        obs = get_last_observation()
        if obs:
            status["last_observation"] = obs.to_dict()
        status["last_action"] = get_self_state("last_action") or ""
        tools_count = len(status.get("last_observation", {}).get("tools_executed", []))
        status["ram_impact"] = "High" if tools_count > 5 else ("Medium" if tools_count > 2 else "Low")
        return jsonify(status)
    except Exception as e:
        return jsonify({
            "error": str(e),
            "planner_confidence": 50,
            "last_action_score": "—",
            "ram_impact": "—",
        })


# --- Sandbox (filesystem + execute) ---
sandbox_bp = Blueprint("sandbox", __name__, url_prefix="/api/sandbox")


def _safe_path(base: Path, path: str) -> Path:
    """Resolve path dentro do sandbox, bloqueando path traversal."""
    base = Path(base).resolve()
    joined = (base / path).resolve()
    if not str(joined).startswith(str(base)):
        raise ValueError("Path inválido")
    return joined


def _record_disk_write() -> None:
    """Registra escrita em disco para auditoria de custo Zeabur."""
    try:
        from core.usage_tracker import record_disk_write
        record_disk_write()
    except Exception:
        pass


@sandbox_bp.post("/files")
def api_sandbox_files():
    """
    File System Bridge: comandos da IA para criar arquivos, pastas ou deletar.
    Body: { action: "create_file"|"create_folder"|"delete", path: str, content?: str }
    """
    data = request.get_json(silent=True) or {}
    action = (data.get("action") or "").strip().lower()
    path = (data.get("path") or "").strip()
    if not action or not path:
        return jsonify({"ok": False, "error": "action e path obrigatórios"}), 400
    if ".." in path or path.startswith("/"):
        return jsonify({"ok": False, "error": "path inválido"}), 400
    sandbox = Path(settings.SANDBOX_DIR)
    sandbox.mkdir(parents=True, exist_ok=True)
    try:
        target = _safe_path(sandbox, path)
        if action == "create_file":
            content = data.get("content", "")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8", errors="replace")
            _record_disk_write()
            try:
                from core.event_bus import emit
                emit("file_changed", path=path, action="create_file")
            except Exception:
                pass
            return jsonify({"ok": True, "action": "create_file", "path": path})
        if action == "create_folder":
            target.mkdir(parents=True, exist_ok=True)
            _record_disk_write()
            return jsonify({"ok": True, "action": "create_folder", "path": path})
        if action == "delete":
            if not target.exists():
                return jsonify({"ok": False, "error": "arquivo ou pasta não existe"}), 404
            if target.is_file():
                target.unlink()
            else:
                import shutil
                shutil.rmtree(target)
            _record_disk_write()
            return jsonify({"ok": True, "action": "delete", "path": path})
        return jsonify({"ok": False, "error": "action deve ser create_file, create_folder ou delete"}), 400
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@sandbox_bp.post("/save")
def api_sandbox_save():
    """Salva arquivos do Workspace no sandbox do servidor."""
    data = request.get_json(silent=True) or {}
    files = data.get("files") or []
    if not isinstance(files, list):
        return jsonify({"ok": False, "error": "files deve ser lista"}), 400
    sandbox = Path(settings.SANDBOX_DIR)
    sandbox.mkdir(parents=True, exist_ok=True)
    saved = []
    for item in files[:50]:
        if not isinstance(item, dict):
            continue
        path = (item.get("path") or "").strip()
        content = item.get("content", "")
        if not path or ".." in path or path.startswith("/"):
            continue
        try:
            target = _safe_path(sandbox, path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8", errors="replace")
            saved.append(path)
            _record_disk_write()
        except Exception as e:
            return jsonify({"ok": False, "error": str(e), "saved": saved}), 400
    for path in saved:
        try:
            from core.event_bus import emit
            emit("file_changed", path=path, action="save")
        except Exception:
            pass
    return jsonify({"ok": True, "saved": saved})


@sandbox_bp.post("/map")
def api_sandbox_generate_map():
    """Project Mapper: gera .yui_map.json com estrutura e dependências."""
    try:
        from core.project_mapper import generate_yui_map
        result = generate_yui_map()
        if result.get("ok"):
            return jsonify(result)
        return jsonify({"ok": False, "error": result.get("error", "erro desconhecido")}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@sandbox_bp.get("/zip")
def api_sandbox_zip():
    """Compacta todo o sandbox e retorna URL de download do ZIP."""
    sandbox = Path(settings.SANDBOX_DIR)
    sandbox.mkdir(parents=True, exist_ok=True)
    files = [p for p in sandbox.rglob("*") if p.is_file()]
    if not files:
        return jsonify({"ok": False, "error": "Sandbox vazio, nada para compactar."}), 400
    settings.GENERATED_PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    zip_name = f"workspace_sandbox_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    zip_path = settings.GENERATED_PROJECTS_DIR / zip_name
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in files:
                zf.write(file_path, file_path.relative_to(sandbox))
        _record_disk_write()
        return jsonify({"ok": True, "filename": zip_name, "url": f"/download/{zip_name}"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@sandbox_bp.get("/read")
def api_sandbox_read():
    """Lê conteúdo de um arquivo no sandbox. Query: path."""
    path_arg = (request.args.get("path") or "").strip()
    if not path_arg or ".." in path_arg or path_arg.startswith("/"):
        return jsonify({"ok": False, "error": "path inválido"}), 400
    sandbox = Path(settings.SANDBOX_DIR)
    try:
        target = _safe_path(sandbox, path_arg)
    except ValueError:
        return jsonify({"ok": False, "error": "path inválido"}), 400
    if not target.exists() or not target.is_file():
        return jsonify({"ok": False, "error": "arquivo não encontrado"}), 404
    try:
        content = target.read_text(encoding="utf-8", errors="replace")
        return jsonify({"ok": True, "path": path_arg, "content": content})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@sandbox_bp.get("/list")
def api_sandbox_list():
    """
    Lazy File Listing: lista apenas o conteúdo direto de uma pasta (não recursivo).
    Query: path (opcional, default "."). Use para expandir pastas sob demanda.
    """
    path_arg = (request.args.get("path") or ".").strip()
    if ".." in path_arg or path_arg.startswith("/"):
        return jsonify({"ok": False, "error": "path inválido"}), 400
    sandbox = Path(settings.SANDBOX_DIR)
    sandbox.mkdir(parents=True, exist_ok=True)
    try:
        target = _safe_path(sandbox, path_arg)
    except ValueError:
        return jsonify({"ok": False, "error": "path inválido"}), 400
    if not target.exists():
        return jsonify({"ok": False, "error": "pasta não existe"}), 404
    if not target.is_dir():
        return jsonify({"ok": False, "error": "não é pasta"}), 400
    ignore = {"__pycache__", ".git", ".venv", "venv", "env", "node_modules", ".mypy_cache", ".pytest_cache", "build", "dist", ".DS_Store", "Thumbs.db", ".yui_map.json"}
    entries = []
    for child in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        if child.name in ignore or (child.name.startswith(".") and child.name not in (".env", ".env.example")):
            continue
        entries.append({
            "name": child.name,
            "path": str(child.relative_to(sandbox)).replace("\\", "/"),
            "is_dir": child.is_dir(),
        })
    return jsonify({"ok": True, "entries": entries})


@sandbox_bp.get("/map")
def api_sandbox_get_map():
    """Retorna .yui_map.json se existir."""
    try:
        from core.project_mapper import get_yui_map
        data = get_yui_map()
        if data:
            return jsonify({"ok": True, "map": data})
        return jsonify({"ok": False, "error": ".yui_map.json não encontrado"}), 404
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@sandbox_bp.post("/lessons")
def api_sandbox_lessons():
    """Memória de Erros: grava correção em .yui_lessons.md quando usuário corrige a IA."""
    data = request.get_json(silent=True) or {}
    error_desc = (data.get("error") or data.get("error_description") or "").strip()
    correction = (data.get("correction") or data.get("fix") or "").strip()
    context = (data.get("context") or "").strip()
    if not error_desc or not correction:
        return jsonify({"ok": False, "error": "error e correction obrigatórios"}), 400
    try:
        from core.lessons_learner import append_lesson
        ok = append_lesson(error_desc, correction, context=context or None)
        return jsonify({"ok": ok}) if ok else jsonify({"ok": False, "error": "Falha ao gravar"}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@sandbox_bp.post("/multi-save")
def api_sandbox_multi_save():
    """
    Multi-Write: salva lote de arquivos com streaming.
    Body: { actions: [{ action: "create"|"update"|"delete", path: str, content?: str }] }
    Processa em chunks para evitar >2GB RAM.
    """
    data = request.get_json(silent=True) or {}
    actions = data.get("actions") or []
    if not isinstance(actions, list):
        return jsonify({"ok": False, "error": "actions deve ser lista"}), 400
    sandbox = Path(settings.SANDBOX_DIR)
    sandbox.mkdir(parents=True, exist_ok=True)
    CHUNK_SIZE = 15
    saved, deleted, errors = [], [], []
    # Validação de sintaxe (Linter) antes de salvar
    try:
        from core.code_linter import lint_multi_write_actions
        _, lint_errors = lint_multi_write_actions(actions)
        if lint_errors:
            return jsonify({
                "ok": False,
                "error": "Erros de sintaxe detectados. Corrija antes de aplicar.",
                "lint_errors": lint_errors[:10],
            }), 400
    except Exception:
        pass
    for i in range(0, min(len(actions), 100), CHUNK_SIZE):
        chunk = actions[i : i + CHUNK_SIZE]
        for item in chunk:
            if not isinstance(item, dict):
                continue
            action = (item.get("action") or "").strip().lower()
            path = (item.get("path") or "").strip()
            if not path or ".." in path or path.startswith("/"):
                errors.append(f"{path}: path inválido")
                continue
            try:
                target = _safe_path(sandbox, path)
                if action == "delete":
                    if target.exists():
                        if target.is_file():
                            target.unlink()
                        else:
                            import shutil
                            shutil.rmtree(target)
                        deleted.append(path)
                        _record_disk_write()
                elif action in ("create", "update"):
                    content = item.get("content", "")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content, encoding="utf-8", errors="replace")
                    saved.append(path)
                    _record_disk_write()
                else:
                    errors.append(f"{path}: action inválida")
            except ValueError as e:
                errors.append(f"{path}: {e}")
            except Exception as e:
                errors.append(f"{path}: {e}")
    for path in saved + deleted:
        try:
            from core.event_bus import emit
            emit("file_changed", path=path, action="multi_save")
        except Exception:
            pass
    return jsonify({"ok": True, "saved": saved, "deleted": deleted, "errors": errors})


@sandbox_bp.post("/deploy")
def api_sandbox_deploy():
    """Deploy via Yui: git add, commit, push no repositório do sandbox."""
    import subprocess
    sandbox = Path(settings.SANDBOX_DIR)
    if not sandbox.is_dir():
        return jsonify({"ok": False, "error": "Sandbox não existe"}), 400
    msg = (request.get_json(silent=True) or {}).get("message") or "Deploy via Yui"
    msg = msg.strip()[:200]
    try:
        r = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(sandbox),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if r.returncode != 0:
            return jsonify({"ok": False, "error": "Não é um repositório git ou git não disponível"}), 400
        if not r.stdout.strip():
            return jsonify({"ok": True, "message": "Nenhuma alteração para commit"})
        subprocess.run(["git", "add", "-A"], cwd=str(sandbox), capture_output=True, timeout=30, check=True)
        subprocess.run(["git", "commit", "-m", msg], cwd=str(sandbox), capture_output=True, timeout=30, check=False)
        r2 = subprocess.run(["git", "push"], cwd=str(sandbox), capture_output=True, text=True, timeout=60)
        if r2.returncode != 0:
            return jsonify({"ok": False, "error": r2.stderr or r2.stdout or "Push falhou"}), 500
        return jsonify({"ok": True, "message": "Deploy concluído com sucesso"})
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "error": "Timeout ao executar git"}), 500
    except FileNotFoundError:
        return jsonify({"ok": False, "error": "Git não encontrado no servidor"}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@sandbox_bp.post("/execute")
def api_sandbox_execute():
    """Executa código via Sandbox Executor (subprocess isolado, timeout, limite RAM)."""
    from datetime import datetime
    from core.sandbox_executor import run_code
    data = request.get_json(silent=True) or {}
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Sao_Paulo")
        executed_at = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        executed_at = datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S")
    code = data.get("code") or ""
    lang = (data.get("lang") or "python").lower()
    timeout = int(data.get("timeout") or 120)
    if timeout > 300:
        timeout = 300
    if not code.strip():
        return jsonify({"ok": False, "stdout": "", "stderr": "Código vazio", "exit_code": -1, "feedback": "", "executed_at": executed_at}), 400

    max_ram_mb = 512 if lang in ("javascript", "js", "node") else 256
    result = run_code(
        code=code,
        lang=lang,
        cwd=Path(settings.SANDBOX_DIR),
        timeout=timeout,
        max_ram_mb=max_ram_mb,
    )

    feedback = result.feedback
    if result.exit_code != 0 and not feedback:
        try:
            from core.self_monitoring import get_system_snapshot
            snap = get_system_snapshot()
            if snap and snap.mode != "normal":
                feedback = f"Servidor sob carga (CPU: {snap.cpu_percent:.0f}%, RAM: {snap.ram_percent:.0f}%)."
        except Exception:
            pass

    return jsonify({
        "ok": result.ok,
        "stdout": result.stdout or "",
        "stderr": result.stderr or "",
        "exit_code": result.exit_code,
        "feedback": feedback,
        "executed_at": executed_at,
    })


# --- Goals (objetivos persistentes) ---
goals_bp = Blueprint("goals", __name__, url_prefix="/api/goals")


@goals_bp.get("/")
def api_list_goals():
    """Lista objetivos ativos."""
    try:
        from core.goals.goal_manager import get_active_goals
        goals = get_active_goals()
        return jsonify({"goals": [g.to_dict() for g in goals]})
    except Exception as e:
        return jsonify({"error": str(e), "goals": []}), 500


@goals_bp.post("/")
def api_add_goal():
    """Adiciona objetivo. Body: {name, priority?, type?}."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name obrigatório"}), 400
    try:
        from core.goals.goal_manager import add_goal, GoalType
        priority = float(data.get("priority", 1.0))
        t = (data.get("type") or "user").lower()
        goal_type = GoalType.USER_GOAL
        if t == "system":
            goal_type = GoalType.SYSTEM_GOAL
        elif t == "self":
            goal_type = GoalType.SELF_IMPROVEMENT
        goal = add_goal(name=name, priority=priority, goal_type=goal_type)
        return jsonify({"ok": True, "goal": goal.to_dict()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- Missions (Project Brain) ---
missions_bp = Blueprint("missions", __name__, url_prefix="/api/missions")


@missions_bp.get("/")
def api_get_active_mission():
    """Retorna missão ativa. Query: user_id, chat_id."""
    user_id = (request.args.get("user_id") or "").strip()
    chat_id = (request.args.get("chat_id") or "").strip()
    try:
        from core.project_manager import get_active_mission
        mission = get_active_mission(user_id=user_id, chat_id=chat_id)
        if mission:
            return jsonify({"ok": True, "mission": mission.to_dict()})
        return jsonify({"ok": True, "mission": None})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "mission": None}), 500


@missions_bp.post("/")
def api_create_mission():
    """Cria missão. Body: project, goal, tasks?, user_id?, chat_id?."""
    data = request.get_json(silent=True) or {}
    project = (data.get("project") or "").strip()
    goal = (data.get("goal") or "").strip()
    if not project or not goal:
        return jsonify({"error": "project e goal obrigatórios"}), 400
    tasks = data.get("tasks") or []
    if isinstance(tasks, str):
        tasks = [t.strip() for t in tasks.split(",") if t.strip()]
    user_id = (data.get("user_id") or "").strip()
    chat_id = (data.get("chat_id") or "").strip()
    try:
        from core.project_manager import create_mission
        mission = create_mission(project=project, goal=goal, tasks=tasks, user_id=user_id, chat_id=chat_id)
        return jsonify({"ok": True, "mission": mission.to_dict()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@missions_bp.patch("/<project>")
def api_update_mission(project: str):
    """Atualiza progresso. Body: task_completed?, progress_delta?, current_task?."""
    data = request.get_json(silent=True) or {}
    task_completed = (data.get("task_completed") or "").strip() or None
    progress_delta = float(data.get("progress_delta", 0))
    current_task = (data.get("current_task") or "").strip() or None
    try:
        from core.project_manager import update_mission_progress
        if update_mission_progress(project, task_completed=task_completed, progress_delta=progress_delta, current_task=current_task):
            return jsonify({"ok": True})
        return jsonify({"error": "Missão não encontrada ou já concluída"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@missions_bp.post("/<project>/complete")
def api_complete_mission(project: str):
    """Marca missão como concluída."""
    try:
        from core.project_manager import complete_mission
        if complete_mission(project):
            return jsonify({"ok": True})
        return jsonify({"error": "Missão não encontrada"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
