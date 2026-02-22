"""
AutoDev Agent — Agente autônomo com controle real do workspace.

- OpenAI API com tool calling
- Modo dry-run: simula execução sem alterar arquivos
- Aprovação automática: executa tools sem confirmação
- Abre PR sozinho: git branch, commit, push, create PR via GitHub API
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

try:
    from config import settings
    WORKSPACE = Path(settings.SANDBOX_DIR)
except Exception:
    WORKSPACE = Path(__file__).resolve().parents[1] / "sandbox"

FORBIDDEN_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build"}
DANGEROUS_CMDS = ["rm -rf", "rm -fr", "del /", "format ", "shutdown", "mkfs", ":(){", "dd if="]


def _safe_path(base: Path, rel: str) -> Path:
    """Resolve path dentro do base, bloqueia path traversal."""
    base = Path(base).resolve()
    joined = (base / rel).resolve()
    if not str(joined).startswith(str(base)):
        raise ValueError("Caminho fora do workspace")
    for part in Path(rel).parts:
        if part.lower() in FORBIDDEN_DIRS:
            raise ValueError(f"Acesso proibido: {part}")
    return joined


# ==========================================================
# SCHEMA DAS TOOLS (OpenAI function calling)
# ==========================================================

AUTODEV_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Lista arquivos e pastas do diretório. Ignora node_modules e .git.",
            "parameters": {
                "type": "object",
                "properties": {"dir": {"type": "string", "description": "Pasta relativa (ex: . ou src)"}},
                "required": ["dir"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Lê conteúdo de um arquivo. Máx 2000 linhas.",
            "parameters": {
                "type": "object",
                "properties": {"file_path": {"type": "string", "description": "Caminho relativo do arquivo"}},
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Escreve em arquivo. Cria backup .bak se já existir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["file_path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Executa comando no terminal. Bloqueia rm -rf, del, format, shutdown.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string", "description": "Comando a executar"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_create_branch",
            "description": "Cria e faz checkout de uma nova branch.",
            "parameters": {
                "type": "object",
                "properties": {"branch_name": {"type": "string"}},
                "required": ["branch_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_add",
            "description": "Adiciona arquivos ao stage (git add).",
            "parameters": {
                "type": "object",
                "properties": {"paths": {"type": "string", "description": "Arquivos ou . para todos"}},
                "required": ["paths"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_commit",
            "description": "Faz commit das alterações em stage.",
            "parameters": {
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_push",
            "description": "Push da branch atual para o remote.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_pr",
            "description": "Abre Pull Request no GitHub. Requer GITHUB_TOKEN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "body": {"type": "string", "description": "Descrição do PR"},
                },
                "required": ["title"],
            },
        },
    },
]


# ==========================================================
# EXECUÇÃO DAS TOOLS (com dry_run e auto_approve)
# ==========================================================

def _exec_list_files(dir_path: str, dry_run: bool) -> Dict[str, Any]:
    if dry_run:
        return {"ok": True, "dry_run": True, "message": f"[DRY-RUN] Listaria arquivos em {dir_path}"}
    try:
        target = _safe_path(WORKSPACE, dir_path or ".")
        if not target.exists() or not target.is_dir():
            return {"ok": False, "error": "Diretório não existe"}
        names = [e.name for e in target.iterdir() if e.name not in FORBIDDEN_DIRS]
        return {"ok": True, "files": sorted(names)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _exec_read_file(file_path: str, dry_run: bool) -> Dict[str, Any]:
    if dry_run:
        return {"ok": True, "dry_run": True, "message": f"[DRY-RUN] Leria arquivo {file_path}"}
    try:
        target = _safe_path(WORKSPACE, file_path)
        if not target.exists() or not target.is_file():
            return {"ok": False, "error": "Arquivo não existe"}
        content = target.read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n")
        if len(lines) > 2000:
            content = "\n".join(lines[:2000]) + "\n# ... (truncado em 2000 linhas)"
        return {"ok": True, "content": content}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _exec_write_file(file_path: str, content: str, dry_run: bool) -> Dict[str, Any]:
    if dry_run:
        return {"ok": True, "dry_run": True, "message": f"[DRY-RUN] Escreveria {len(content)} chars em {file_path}"}
    try:
        target = _safe_path(WORKSPACE, file_path)
        if target.exists() and target.is_file():
            backup = target.with_suffix(target.suffix + ".bak")
            backup.write_text(target.read_text(encoding="utf-8", errors="replace"), encoding="utf-8", errors="replace")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", errors="replace")
        return {"ok": True, "path": str(target)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _exec_run_command(command: str, dry_run: bool) -> Dict[str, Any]:
    cmd_lower = (command or "").strip().lower()
    for dangerous in DANGEROUS_CMDS:
        if dangerous.lower() in cmd_lower:
            return {"ok": False, "error": f"Comando bloqueado: {dangerous}"}
    if dry_run:
        return {"ok": True, "dry_run": True, "message": f"[DRY-RUN] Executaria: {command}"}
    try:
        r = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(WORKSPACE),
        )
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        if r.returncode != 0:
            return {"ok": False, "error": err or out or f"exit code {r.returncode}", "stdout": out}
        return {"ok": True, "stdout": out}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Timeout (120s)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _exec_git_create_branch(branch_name: str, dry_run: bool) -> Dict[str, Any]:
    if dry_run:
        return {"ok": True, "dry_run": True, "message": f"[DRY-RUN] Criaria branch {branch_name}"}
    try:
        subprocess.run(
            ["git", "checkout", "-b", branch_name.strip()],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(WORKSPACE),
            check=True,
        )
        return {"ok": True, "branch": branch_name}
    except subprocess.CalledProcessError as e:
        return {"ok": False, "error": e.stderr or str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _exec_git_add(paths: str, dry_run: bool) -> Dict[str, Any]:
    if dry_run:
        return {"ok": True, "dry_run": True, "message": f"[DRY-RUN] git add {paths}"}
    try:
        subprocess.run(
            ["git", "add", paths.strip() or "."],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(WORKSPACE),
            check=True,
        )
        return {"ok": True}
    except subprocess.CalledProcessError as e:
        return {"ok": False, "error": e.stderr or str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _exec_git_commit(message: str, dry_run: bool) -> Dict[str, Any]:
    if dry_run:
        return {"ok": True, "dry_run": True, "message": f"[DRY-RUN] git commit -m \"{message[:50]}...\""}
    try:
        subprocess.run(
            ["git", "commit", "-m", message.strip()[:500]],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(WORKSPACE),
            check=True,
        )
        return {"ok": True}
    except subprocess.CalledProcessError as e:
        return {"ok": False, "error": e.stderr or str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _exec_git_push(dry_run: bool) -> Dict[str, Any]:
    if dry_run:
        return {"ok": True, "dry_run": True, "message": "[DRY-RUN] git push"}
    try:
        subprocess.run(
            ["git", "push", "-u", "origin", "HEAD"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(WORKSPACE),
            check=True,
        )
        return {"ok": True}
    except subprocess.CalledProcessError as e:
        return {"ok": False, "error": e.stderr or str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _exec_create_pr(title: str, body: str, dry_run: bool) -> Dict[str, Any]:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        try:
            from config import settings
            token = getattr(settings, "GITHUB_TOKEN", None)
        except Exception:
            pass
    if not token:
        return {"ok": False, "error": "GITHUB_TOKEN não configurado"}
    if dry_run:
        return {"ok": True, "dry_run": True, "message": f"[DRY-RUN] Abriria PR: {title}"}
    try:
        import urllib.request
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(WORKSPACE),
        )
        head_branch = (r.stdout or "").strip()
        r = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            cwd=str(WORKSPACE),
        )
        url = (r.stdout or "").strip()
        if "github.com" not in url:
            return {"ok": False, "error": "Remote origin não é GitHub"}
        parts = url.replace("https://github.com/", "").replace("git@github.com:", "").replace(".git", "").strip().split("/")
        if len(parts) < 2:
            return {"ok": False, "error": "Não foi possível extrair owner/repo"}
        owner, repo = parts[0], parts[1]
        base = "main"
        data = json.dumps({
            "title": title.strip()[:200],
            "body": (body or "").strip()[:4000],
            "head": head_branch,
            "base": base,
        }).encode()
        req = urllib.request.Request(
            f"https://api.github.com/repos/{owner}/{repo}/pulls",
            data=data,
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
        return {"ok": True, "url": result.get("html_url", ""), "number": result.get("number")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def execute_autodev_tool(name: str, args: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    """Executa uma tool do AutoDev. Retorna dict com ok, result/error."""
    try:
        from config import settings
        dry_run = dry_run or getattr(settings, "AUTODEV_DRY_RUN", False)
    except Exception:
        pass

    handlers = {
        "list_files": lambda: _exec_list_files(args.get("dir", "."), dry_run),
        "read_file": lambda: _exec_read_file(args.get("file_path", ""), dry_run),
        "write_file": lambda: _exec_write_file(args.get("file_path", ""), args.get("content", ""), dry_run),
        "run_command": lambda: _exec_run_command(args.get("command", ""), dry_run),
        "git_create_branch": lambda: _exec_git_create_branch(args.get("branch_name", ""), dry_run),
        "git_add": lambda: _exec_git_add(args.get("paths", "."), dry_run),
        "git_commit": lambda: _exec_git_commit(args.get("message", ""), dry_run),
        "git_push": lambda: _exec_git_push(dry_run),
        "create_pr": lambda: _exec_create_pr(args.get("title", ""), args.get("body", ""), dry_run),
    }
    fn = handlers.get(name)
    if not fn:
        return {"ok": False, "error": f"Tool desconhecida: {name}"}
    return fn()


# ==========================================================
# AGENTE AUTODEV (OpenAI + tool calling)
# ==========================================================

AUTODEV_SYSTEM_PROMPT = """Você é um agente de desenvolvimento autônomo (AutoDev).
Você pode: listar arquivos, ler arquivos, escrever arquivos, executar comandos no terminal,
criar branches, fazer commit, push e abrir Pull Requests no GitHub.

Regras:
- Trabalhe apenas dentro do workspace. Nunca acesse node_modules ou .git.
- Ao modificar código, faça alterações incrementais e testáveis.
- Ao abrir PR, use título claro e descrição com o que foi alterado.
- Se algo falhar, explique o erro e sugira correção.
"""


def run_autodev(
    user_message: str,
    dry_run: bool = False,
    auto_approve: bool = True,
    max_iterations: int = 10,
) -> Generator[str, None, None]:
    """
    Executa o agente AutoDev: OpenAI com tool calling.
    - dry_run: simula tools sem executar
    - auto_approve: executa tools sem pedir confirmação (sempre True quando dry_run=False)
    """
    try:
        from config import settings
        api_key = getattr(settings, "OPENAI_API_KEY", None) or os.environ.get("OPENAI_API_KEY")
        dry_run = dry_run or getattr(settings, "AUTODEV_DRY_RUN", False)
        auto_approve = auto_approve or getattr(settings, "AUTODEV_AUTO_APPROVE", True)
    except Exception:
        api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        yield "⚠️ OPENAI_API_KEY não configurada."
        return

    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": AUTODEV_SYSTEM_PROMPT + (f"\n[MODO DRY-RUN] Simule todas as ações. Não execute nada de verdade." if dry_run else "")},
        {"role": "user", "content": user_message},
    ]

    for _ in range(max_iterations):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=AUTODEV_TOOLS_SCHEMA,
                tool_choice="auto",
                temperature=0.2,
                max_tokens=4096,
            )
        except Exception as e:
            yield f"Erro ao chamar OpenAI: {e}"
            return

        choice = response.choices[0] if response.choices else None
        if not choice:
            yield "Resposta vazia da IA."
            return

        msg = choice.message
        content = (msg.content or "").strip()
        tool_calls = getattr(msg, "tool_calls", None) or []

        if content:
            yield content

        if not tool_calls:
            return

        tool_calls_list = []
        for tc in tool_calls:
            fc = {"name": tc.function.name, "arguments": tc.function.arguments or "{}"}
            tool_calls_list.append({"id": tc.id, "type": "function", "function": fc})
        messages.append({
            "role": "assistant",
            "content": content or None,
            "tool_calls": tool_calls_list,
        })

        for tc in tool_calls:
            name = tc.function.name
            args_str = tc.function.arguments or "{}"
            try:
                args = json.loads(args_str)
            except json.JSONDecodeError:
                args = {}
            result = execute_autodev_tool(name, args, dry_run=dry_run)
            result_str = json.dumps(result, ensure_ascii=False)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_str,
            })
            if not auto_approve and not dry_run:
                yield f"\n[Tool {name}] Executado. Resultado: {result_str[:200]}...\n"
            elif result.get("dry_run"):
                yield f"\n[DRY-RUN] {result.get('message', name)}\n"
