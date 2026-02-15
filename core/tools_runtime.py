"""
Implementações das ferramentas (tools) executáveis pela Yui.
Sempre usa Path absoluto (BASE_DIR do config) para evitar bug no Render/cwd.
"""

import os
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None  # Python < 3.9

from yui_ai.analyzer.report_formatter import run_file_analysis, report_to_text
from yui_ai.project_analysis.analysis_report import executar_analise_completa
from yui_ai.project_analysis.project_scanner import escanear_estrutura
from yui_ai.project_analysis.project_index import get_or_compute

try:
    from config import settings
    PROJECT_ROOT = Path(settings.BASE_DIR).resolve()
    GENERATED_ROOT = Path(settings.GENERATED_PROJECTS_DIR).resolve()
    SANDBOX_ROOT = Path(settings.SANDBOX_DIR).resolve()
except Exception:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    GENERATED_ROOT = PROJECT_ROOT / "generated_projects"
    SANDBOX_ROOT = PROJECT_ROOT / "sandbox"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"


def get_current_time() -> Dict[str, Any]:
    """
    Retorna o horário atual em Brasília/São Paulo.
    Chamada leve, sem I/O pesado — otimizada para tempo real.
    """
    try:
        tz = ZoneInfo("America/Sao_Paulo") if ZoneInfo else None
        if tz:
            now = datetime.now(tz)
        else:
            import time
            now = datetime.fromtimestamp(time.time())
        return {
            "ok": True,
            "datetime_brasilia": now.strftime("%d/%m/%Y %H:%M:%S"),
            "iso": now.isoformat(),
            "date": now.strftime("%d/%m/%Y"),
            "time": now.strftime("%H:%M:%S"),
            "timezone": "America/Sao_Paulo",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_get_current_time() -> Dict[str, Any]:
    """Wrapper para a ferramenta get_current_time (sem args)."""
    return get_current_time()


def tool_buscar_web(query: str, limite: int = 5) -> Dict[str, Any]:
    """
    Busca informações na web via DuckDuckGo.
    Use quando precisar verificar dados externos ou informações recentes.
    """
    if not query or not str(query).strip():
        return {"ok": False, "resultados": [], "error": "query obrigatória"}
    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(str(query).strip(), max_results=min(limite, 10)))
        return {
            "ok": True,
            "resultados": [
                {
                    "titulo": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "resumo": r.get("body", ""),
                    "url": r.get("href", ""),
                    "link": r.get("href", ""),
                }
                for r in (results or [])
            ],
        }
    except ImportError:
        return {
            "ok": False,
            "resultados": [],
            "error": "Instale duckduckgo-search: pip install duckduckgo-search",
        }
    except Exception as e:
        return {"ok": False, "resultados": [], "error": str(e)}


def tool_analisar_arquivo(filename: str, content: str) -> Dict[str, Any]:
    """
    Analisa um arquivo usando o pipeline existente da Yui.

    Args:
        filename: nome do arquivo (ex: main.py)
        content: conteúdo completo do arquivo em texto

    Returns:
        dict com { ok: bool, report: dict|None, text: str, error: str|None }
    """
    if not filename:
        return {"ok": False, "report": None, "text": "", "error": "filename obrigatório"}
    if content is None:
        return {"ok": False, "report": None, "text": "", "error": "content obrigatório"}

    try:
        ok, report, err = run_file_analysis(content.encode("utf-8", errors="ignore"), filename)
        if not ok or not report:
            return {"ok": False, "report": None, "text": "", "error": err or "Falha na análise do arquivo."}
        text = report_to_text(report)
        return {"ok": True, "report": report, "text": text, "error": None}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "report": None, "text": "", "error": str(e)}


def tool_analisar_projeto(raiz: Optional[str] = None) -> Dict[str, Any]:
    """
    Executa uma análise arquitetural completa do projeto (somente leitura).

    Args:
        raiz: caminho raiz do projeto; se None, usa DEFAULT_PROJECT_ROOT interno.

    Returns:
        dict com { ok: bool, dados: dict|None, texto: str, error: str|None }
    """
    try:
        ok, dados, err = get_or_compute(raiz)
        if not ok or not dados:
            return {"ok": False, "dados": None, "texto": "", "error": err or "Falha na análise do projeto."}
        texto = dados.get("texto_formatado") or ""
        return {"ok": True, "dados": dados, "texto": texto, "error": None}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "dados": None, "texto": "", "error": str(e)}


def tool_observar_ambiente(raiz: Optional[str] = None) -> Dict[str, Any]:
    """
    Observador de ambiente: faz uma leitura rápida da estrutura do projeto
    e gera um pequeno resumo com frameworks/projeto detectados.
    """
    try:
        scanner = escanear_estrutura(raiz)
        raiz_real = scanner.get("raiz", "")
        modulos = scanner.get("modulos_principais", [])
        extensoes = scanner.get("extensoes", {})
        total = scanner.get("total_arquivos", 0)

        linguagens = []
        if ".py" in extensoes:
            linguagens.append("Python")
        if ".js" in extensoes or ".ts" in extensoes:
            linguagens.append("JavaScript/TypeScript")
        if ".html" in extensoes:
            linguagens.append("HTML")
        if ".css" in extensoes:
            linguagens.append("CSS")

        frameworks = []
        if "web_server.py" in (scanner.get("arquivos_por_pasta", {}).get("[raiz]", []) or []):
            frameworks.append("Flask (web_server.py)")
        if "yui_ai" in modulos:
            frameworks.append("Pacote Yui AI (assistente autônoma)")

        resumo = f"Raiz do projeto: {raiz_real or 'desconhecida'}. Total de arquivos: {total}."
        if linguagens:
            resumo += f" Linguagens principais: {', '.join(linguagens)}."
        if modulos:
            resumo += f" Módulos principais: {', '.join(modulos)}."
        sugestao = ""
        if frameworks:
            sugestao = (
                "Detectei estes componentes/frameworks: "
                + ", ".join(frameworks)
                + ". Você pode pedir: 'analisa a arquitetura do projeto' para um relatório completo."
            )

        return {
            "ok": True,
            "resumo": resumo,
            "frameworks": frameworks,
            "linguagens": linguagens,
            "sugestao": sugestao,
            "error": None,
        }
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "resumo": "", "frameworks": [], "linguagens": [], "sugestao": "", "error": str(e)}


def _sanitize_code(path: str, content: str) -> str:
    """Remove usos diretos de eval() comentando as linhas, por segurança."""
    if not content:
        return ""
    ext = Path(path).suffix.lower()
    is_js = ext in {".js", ".ts", ".tsx", ".jsx"}
    comment_prefix = "//" if is_js else "#"
    linhas = []
    for linha in content.splitlines():
        if "eval(" in linha:
            linhas.append(f"{comment_prefix} [Yui] eval removido por segurança; linha original comentada:")
            linhas.append(f"{comment_prefix} {linha}")
        else:
            linhas.append(linha)
    return "\n".join(linhas)


def _normalize_files(files: Any) -> list:
    """Converte files para lista de dicts; aceita JSON string, dict único ou lista."""
    if isinstance(files, list):
        return files
    if isinstance(files, str) and files.strip():
        try:
            import json
            parsed = json.loads(files)
            return parsed if isinstance(parsed, list) else [parsed] if isinstance(parsed, dict) else []
        except Exception:
            pass
    if isinstance(files, dict):
        # Um único arquivo {path, content} ou {files: [...]}
        if "path" in files or "content" in files:
            return [files]
        if "files" in files:
            return _normalize_files(files["files"])
    return []


def tool_criar_projeto_arquivos(root_dir: str, files: Any) -> Dict[str, Any]:
    """
    Cria fisicamente um mini-projeto a partir de uma lista de arquivos.

    Args:
        root_dir: nome/base da pasta do projeto (relativa a generated_projects).
        files: lista de dicts { "path": "subpasta/arquivo.ext", "content": "..." }.
    """
    if not root_dir:
        root_dir = "projeto-yui"
    slug = "".join(c if c.isalnum() or c in ("-", "_") else "-" for c in root_dir).strip("-") or "projeto-yui"
    base = GENERATED_ROOT / slug
    created: list[str] = []
    try:
        base.mkdir(parents=True, exist_ok=True)
        files_list = _normalize_files(files) if files is not None else []
        if not files_list:
            return {"ok": False, "root": str(base), "files": [], "error": "Parametro 'files' deve ser lista de {path, content} (ex: [{\"path\":\"index.html\",\"content\":\"...\"}])."}
        for item in files_list:
            if not isinstance(item, dict):
                continue
            rel_path = (item.get("path") or "").strip()
            content = item.get("content") or ""
            if not rel_path:
                continue
            # Proteção contra paths maliciosos
            destino = (base / rel_path).resolve()
            try:
                destino.relative_to(base)
            except Exception:
                continue
            destino.parent.mkdir(parents=True, exist_ok=True)
            safe_content = _sanitize_code(rel_path, content)
            with open(destino, "w", encoding="utf-8") as f:
                f.write(safe_content)
            created.append(str(destino.relative_to(PROJECT_ROOT)))
        return {"ok": True, "root": str(base), "files": created, "error": None}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "root": str(base), "files": created, "error": str(e)}


def _resolve_project_dir(root_dir: str) -> Optional[Path]:
    """
    Resolve root_dir para um Path absoluto da pasta do projeto.
    Projetos gerados ficam em GENERATED_ROOT (generated_projects/).
    No Render/Zeabur, cwd pode ser outro; por isso SEMPRE usamos BASE_DIR absoluto.
    """
    if not root_dir or not root_dir.strip():
        return None
    root_dir = root_dir.strip()
    p = Path(root_dir)
    # 1) Já é absoluto e existe
    if p.is_absolute() and p.is_dir():
        return p
    # 2) Nome da pasta só (ex: calculadora) -> em generated_projects/
    candidate = (GENERATED_ROOT / root_dir).resolve()
    if candidate.is_dir():
        return candidate
    # 3) root_dir era path completo; extrai slug e procura em generated_projects
    slug = p.name
    if slug:
        candidate = (GENERATED_ROOT / slug).resolve()
        if candidate.is_dir():
            return candidate
    # 4) Se root_dir contém "generated_projects", extrai o slug final
    if "generated_projects" in root_dir or "generated_projects" in root_dir.replace("\\", "/"):
        parts = root_dir.replace("\\", "/").split("/")
        for i, part in enumerate(parts):
            if part == "generated_projects" and i + 1 < len(parts):
                slug = parts[i + 1]
                if slug:
                    candidate = (GENERATED_ROOT / slug).resolve()
                    if candidate.is_dir():
                        return candidate
                break
    # 5) Relativo à raiz do app
    candidate = (PROJECT_ROOT / root_dir).resolve()
    if candidate.is_dir():
        return candidate
    return None


def _latest_generated_project_dir() -> Optional[Path]:
    """Retorna a pasta de projeto mais recente em generated_projects/."""
    try:
        GENERATED_ROOT.mkdir(parents=True, exist_ok=True)
        dirs = [p for p in GENERATED_ROOT.iterdir() if p.is_dir()]
        if not dirs:
            return None
        dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return dirs[0]
    except Exception:
        return None


def tool_criar_zip_projeto(
    root_dir: str,
    zip_name: Optional[str] = None,
    background: bool = True,
) -> Dict[str, Any]:
    """
    Gera um script Python para compactar um projeto em ZIP.
    Usa sempre Path absoluto (BASE_DIR) para funcionar no Render.
    background=True (padrão): agenda no scheduler, não bloqueia o chat.
    """
    root_path = _resolve_project_dir(root_dir) if (root_dir and root_dir.strip()) else None
    if not root_path:
        # Fallback útil para prompts como "compacte" sem informar a pasta.
        root_path = _latest_generated_project_dir()
    if not root_path or not root_path.is_dir():
        return {"ok": False, "script_path": "", "zip_output": "", "command": "", "error": "Pasta do projeto não encontrada."}

    try:
        root_path.relative_to(PROJECT_ROOT)
    except Exception:
        return {"ok": False, "script_path": "", "zip_output": "", "command": "", "error": "Pasta fora da raiz do projeto."}

    slug = "".join(c if c.isalnum() or c in ("-", "_") else "-" for c in (zip_name or root_path.name)).strip("-") or "projeto-yui"
    SCRIPTS_ROOT.mkdir(parents=True, exist_ok=True)
    script_path = SCRIPTS_ROOT / f"make_zip_{slug}.py"
    zip_output = root_path.parent / f"{slug}.zip"
    zip_basename = zip_output.name
    download_url = f"/download/{zip_basename}"

    ignore_names = {".env", ".env.example", "venv", ".venv", "__pycache__", "node_modules"}
    ignore_suffixes = {".key", ".pem", ".pfx"}

    script_code = f"""import os
import zipfile
from pathlib import Path

ROOT = Path({repr(str(root_path))}).resolve()
ZIP_PATH = Path({repr(str(zip_output))}).resolve()

IGNORE_NAMES = {sorted(ignore_names)!r}
IGNORE_SUFFIXES = {sorted(ignore_suffixes)!r}


def _should_skip(path: Path) -> bool:
    name = path.name
    if name in IGNORE_NAMES:
        return True
    if path.suffix in IGNORE_SUFFIXES:
        return True
    return False


def make_zip() -> None:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as z:
        for p in ROOT.rglob("*"):
            rel = p.relative_to(ROOT)
            if any(part in IGNORE_NAMES for part in rel.parts):
                continue
            if _should_skip(p):
                continue
            if p.is_file():
                z.write(p, rel)


if __name__ == "__main__":
    print(f"Criando zip em {{ZIP_PATH}} a partir de {{ROOT}}...")
    make_zip()
    print("OK.")
"""

    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_code)
        command = f"python {script_path.relative_to(PROJECT_ROOT)}"
        base_result = {
            "ok": True,
            "script_path": str(script_path),
            "zip_output": str(zip_output),
            "command": command,
            "error": None,
        }
        if background:
            # Agenda no scheduler — não bloqueia o chat.
            # Se scheduler falhar/indisponível, usa thread local como fallback.
            def _run_zip(data):
                spath = Path(data["script_path"])
                durl = data["download_url"]
                zpath = Path(data["zip_output"])
                try:
                    proc = subprocess.run(
                        [sys.executable, str(spath)],
                        cwd=str(PROJECT_ROOT),
                        timeout=60,
                        capture_output=True,
                        check=False,
                    )
                    if proc.returncode != 0 or not zpath.exists() or zpath.stat().st_size == 0:
                        return
                    try:
                        from core.event_bus import emit
                        from core.pending_downloads import add_ready
                        add_ready(durl)
                        emit("zip_ready", download_url=durl)
                    except Exception:
                        pass
                except Exception:
                    pass

            job_data = {
                "script_path": str(script_path),
                "download_url": download_url,
                "zip_output": str(zip_output),
            }
            scheduled = False
            try:
                from core.task_scheduler import get_scheduler
                get_scheduler().add(_run_zip, data=job_data)
                scheduled = True
            except Exception:
                scheduled = False

            if not scheduled:
                try:
                    import threading
                    threading.Thread(target=_run_zip, args=(job_data,), daemon=True).start()
                except Exception:
                    pass

            return {**base_result, "zip_pending": True, "download_url": download_url}
        # Síncrono (background=False)
        try:
            subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(PROJECT_ROOT),
                timeout=60,
                capture_output=True,
                check=False,
            )
        except Exception:
            pass
        return base_result
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "script_path": "", "zip_output": "", "command": "", "error": str(e)}


def tool_consultar_indice_projeto(raiz: Optional[str] = None) -> Dict[str, Any]:
    """
    Consulta o índice de análise de projeto (se existir), sem reprocessar tudo.
    Retorna um resumo enxuto: visão geral, pontos fortes/fracos, riscos e roadmap curto.
    """
    ok, dados, err = get_or_compute(raiz)
    if not ok or not dados:
        return {"ok": False, "resumo": "", "error": err or "Falha ao consultar índice do projeto."}
    resumo = {
        "visao_geral": dados.get("visao_geral", ""),
        "pontos_fortes": dados.get("pontos_fortes", []),
        "pontos_fracos": dados.get("pontos_fracos", []),
        "riscos_tecnicos": dados.get("riscos_tecnicos", []),
        "sugestoes_melhoria": dados.get("sugestoes_melhoria", []),
        "roadmap_curto_prazo": (dados.get("roadmap") or {}).get("curto_prazo", []),
        "score_qualidade": dados.get("score_qualidade", {}),
    }
    return {"ok": True, "dados": resumo, "error": None}


def _safe_sandbox_path(path: str) -> Path:
    """Resolve path dentro do sandbox, bloqueando path traversal."""
    path = (path or "").strip()
    if not path or ".." in path or path.startswith("/"):
        raise ValueError("path inválido")
    target = (SANDBOX_ROOT / path).resolve()
    if not str(target).startswith(str(SANDBOX_ROOT)):
        raise ValueError("path fora do sandbox")
    return target


def tool_fs_create_file(path: str, content: str = "") -> Dict[str, Any]:
    """
    File System Bridge: cria arquivo no sandbox do projeto.
    Use quando precisar criar ou sobrescrever um arquivo.
    """
    try:
        target = _safe_sandbox_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content or "", encoding="utf-8", errors="replace")
        try:
            from core.usage_tracker import record_disk_write
            record_disk_write()
        except Exception:
            pass
        return {"ok": True, "path": path, "action": "create_file"}
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_fs_create_folder(path: str) -> Dict[str, Any]:
    """
    File System Bridge: cria pasta no sandbox do projeto.
    """
    try:
        target = _safe_sandbox_path(path)
        target.mkdir(parents=True, exist_ok=True)
        try:
            from core.usage_tracker import record_disk_write
            record_disk_write()
        except Exception:
            pass
        return {"ok": True, "path": path, "action": "create_folder"}
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_generate_project_map(root: Optional[str] = None) -> Dict[str, Any]:
    """
    Project Mapper: gera .yui_map.json com estrutura e dependências do projeto.
    Leitura sob demanda para evitar >2GB RAM.
    """
    try:
        from core.project_mapper import generate_yui_map
        r = Path(root).resolve() if root else SANDBOX_ROOT
        result = generate_yui_map(r)
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_fs_delete_file(path: str) -> Dict[str, Any]:
    """
    File System Bridge: deleta arquivo ou pasta no sandbox do projeto.
    """
    try:
        import shutil
        target = _safe_sandbox_path(path)
        if not target.exists():
            return {"ok": False, "error": "arquivo ou pasta não existe"}
        if target.is_file():
            target.unlink()
        else:
            shutil.rmtree(target)
        try:
            from core.usage_tracker import record_disk_write
            record_disk_write()
        except Exception:
            pass
        return {"ok": True, "path": path, "action": "delete"}
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

