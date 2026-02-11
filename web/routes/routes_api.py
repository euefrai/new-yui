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
