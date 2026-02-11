"""
Implementações das ferramentas (tools) executáveis pela Yui.

Estas funções são registradas em core.tools_registry.
"""

import os
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional

from yui_ai.analyzer.report_formatter import run_file_analysis, report_to_text
from yui_ai.project_analysis.analysis_report import executar_analise_completa
from yui_ai.project_analysis.project_scanner import escanear_estrutura
from yui_ai.project_analysis.project_index import get_or_compute


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GENERATED_ROOT = PROJECT_ROOT / "generated_projects"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"


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
        if not isinstance(files, list):
            return {"ok": False, "root": str(base), "files": [], "error": "Parametro 'files' deve ser lista."}
        for item in files:
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


def tool_criar_zip_projeto(root_dir: str, zip_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Gera um script Python para compactar um projeto em ZIP.

    Args:
        root_dir: pasta do projeto (relativa ao PROJECT_ROOT ou generated_projects).
        zip_name: nome opcional do zip (sem extensão).
    """
    if not root_dir:
        return {"ok": False, "script_path": "", "zip_output": "", "command": "", "error": "root_dir obrigatório"}
    root_path = (PROJECT_ROOT / root_dir).resolve()
    if not root_path.is_dir():
        alt = (GENERATED_ROOT / root_dir).resolve()
        if alt.is_dir():
            root_path = alt
        else:
            return {"ok": False, "script_path": "", "zip_output": "", "command": "", "error": "Pasta do projeto não encontrada."}

    try:
        root_path.relative_to(PROJECT_ROOT)
    except Exception:
        return {"ok": False, "script_path": "", "zip_output": "", "command": "", "error": "Pasta fora da raiz do projeto."}

    slug = "".join(c if c.isalnum() or c in ("-", "_") else "-" for c in (zip_name or root_path.name)).strip("-") or "projeto-yui"
    SCRIPTS_ROOT.mkdir(parents=True, exist_ok=True)
    script_path = SCRIPTS_ROOT / f"make_zip_{slug}.py"
    zip_output = root_path.parent / f"{slug}.zip"

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
        # Executa o script para gerar o .zip imediatamente (link de download clicável)
        try:
            subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(PROJECT_ROOT),
                timeout=60,
                capture_output=True,
                check=False,
            )
        except Exception:
            pass  # zip_output ainda é retornado; o usuário pode rodar o comando manualmente
        return {
            "ok": True,
            "script_path": str(script_path),
            "zip_output": str(zip_output),
            "command": command,
            "error": None,
        }
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


