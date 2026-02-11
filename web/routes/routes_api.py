# Rotas de API: index, estáticos, download, clear_chat, upload, analyze, tools.

from pathlib import Path

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
        snap = get_system_snapshot(use_cache=False)
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


# --- Sandbox (filesystem + execute) ---
sandbox_bp = Blueprint("sandbox", __name__, url_prefix="/api/sandbox")


def _safe_path(base: Path, path: str) -> Path:
    """Resolve path dentro do sandbox, bloqueando path traversal."""
    base = Path(base).resolve()
    joined = (base / path).resolve()
    if not str(joined).startswith(str(base)):
        raise ValueError("Path inválido")
    return joined


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
        except Exception as e:
            return jsonify({"ok": False, "error": str(e), "saved": saved}), 400
    return jsonify({"ok": True, "saved": saved})


@sandbox_bp.post("/execute")
def api_sandbox_execute():
    """Executa código no sandbox de forma segura (timeout, captura stdout/stderr)."""
    import subprocess
    from datetime import datetime
    data = request.get_json(silent=True) or {}
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Sao_Paulo")
        executed_at = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        executed_at = datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S")
    code = data.get("code") or ""
    lang = (data.get("lang") or "python").lower()
    timeout = int(data.get("timeout") or 15)
    if timeout > 30:
        timeout = 30
    if not code.strip():
        return jsonify({"ok": False, "stdout": "", "stderr": "Código vazio", "exit_code": -1, "feedback": "", "executed_at": executed_at}), 400

    sandbox = Path(settings.SANDBOX_DIR)
    sandbox.mkdir(parents=True, exist_ok=True)
    feedback = ""

    try:
        if lang in ("python", "py"):
            script_path = sandbox / "_run_script.py"
            script_path.write_text(code, encoding="utf-8", errors="replace")
            result = subprocess.run(
                ["python", str(script_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(sandbox),
            )
        elif lang in ("javascript", "js", "node"):
            script_path = sandbox / "_run_script.js"
            script_path.write_text(code, encoding="utf-8", errors="replace")
            result = subprocess.run(
                ["node", str(script_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(sandbox),
            )
        else:
            return jsonify({"ok": False, "stdout": "", "stderr": f"Linguagem '{lang}' não suportada. Use python ou javascript.", "exit_code": -1, "feedback": ""}), 400

        if result.returncode != 0:
            try:
                from core.self_monitoring import get_system_snapshot
                snap = get_system_snapshot()
                if snap and snap.mode != "normal":
                    feedback = f"Servidor sob carga (CPU: {snap.cpu_percent:.0f}%, RAM: {snap.ram_percent:.0f}%). A execução pode ter sido limitada."
            except Exception:
                pass

        return jsonify({
            "ok": result.returncode == 0,
            "stdout": result.stdout or "",
            "stderr": result.stderr or "",
            "exit_code": result.returncode,
            "feedback": feedback,
            "executed_at": executed_at,
        })
    except subprocess.TimeoutExpired:
        try:
            from core.self_monitoring import get_system_snapshot
            snap = get_system_snapshot()
            feedback = f"Timeout ({timeout}s). Servidor: CPU {snap.cpu_percent:.0f}%, RAM {snap.ram_percent:.0f}%."
        except Exception:
            feedback = f"Timeout ({timeout}s). Considere simplificar o código."
        return jsonify({"ok": False, "stdout": "", "stderr": "Timeout na execução", "exit_code": -1, "feedback": feedback, "executed_at": executed_at}), 400
    except FileNotFoundError:
        return jsonify({"ok": False, "stdout": "", "stderr": "Python/Node não encontrado no servidor", "exit_code": -1, "feedback": "", "executed_at": executed_at}), 400
    except Exception as e:
        return jsonify({"ok": False, "stdout": "", "stderr": str(e), "exit_code": -1, "feedback": "", "executed_at": executed_at}), 500


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
