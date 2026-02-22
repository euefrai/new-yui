"""
Yui Tools — Implementação das ferramentas técnicas.
- analisar_codigo: vulnerabilidades, más práticas, arquitetura
- sugerir_arquitetura: estrutura de pastas e responsabilidades
- calcular_custo_estimado: estimativa de custo em tokens
- resumir_contexto: resumo técnico para memória
- listar_arquivos_workspace: lista arquivos do workspace (sandbox)
- ler_arquivo_workspace: lê arquivo do workspace
- escrever_arquivo_workspace: escreve no workspace (com backup)
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

FORBIDDEN_DIRS = {"node_modules", ".git", "dist", "build", ".next", "coverage", "__pycache__"}
BACKUP_DIR = ".yui-backups"


def _get_sandbox() -> Path:
    """Retorna o diretório do workspace (sandbox)."""
    try:
        from config.settings import SANDBOX_DIR
        return Path(SANDBOX_DIR)
    except Exception:
        return Path(__file__).resolve().parents[1] / ".." / "sandbox"


def _safe_path(base: Path, rel_path: str) -> Path:
    """Resolve path dentro do base, bloqueando path traversal."""
    rel_path = (rel_path or ".").replace("\\", "/").lstrip("/")
    if ".." in rel_path or rel_path.startswith("/"):
        raise ValueError("Path inválido")
    base_resolved = base.resolve()
    full = (base_resolved / rel_path).resolve()
    try:
        full.relative_to(base_resolved)
    except ValueError:
        raise ValueError("Path fora do workspace")
    return full


def listar_arquivos_workspace(pasta: str = ".") -> Dict[str, Any]:
    """
    Lista arquivos do workspace (sandbox).
    pasta: caminho relativo ao sandbox.
    """
    try:
        sandbox = _get_sandbox()
        target = _safe_path(sandbox, pasta)
        if not target.is_dir():
            return {"ok": False, "arquivos": [], "erro": f"Pasta não encontrada: {pasta}"}

        arquivos: List[str] = []
        for p in target.rglob("*"):
            if p.is_file():
                rel = p.relative_to(sandbox)
                parts = rel.parts
                if any(part.lower() in FORBIDDEN_DIRS for part in parts):
                    continue
                arquivos.append(str(rel).replace("\\", "/"))
        return {"ok": True, "arquivos": sorted(arquivos)[:200], "erro": None}
    except ValueError as e:
        return {"ok": False, "arquivos": [], "erro": str(e)}
    except Exception as e:
        return {"ok": False, "arquivos": [], "erro": str(e)}


def ler_arquivo_workspace(caminho: str, max_chars: int = 8000) -> Dict[str, Any]:
    """Lê conteúdo de um arquivo do workspace."""
    try:
        sandbox = _get_sandbox()
        target = _safe_path(sandbox, caminho)
        if not target.is_file():
            return {"ok": False, "conteudo": "", "erro": f"Arquivo não encontrado: {caminho}"}
        content = target.read_text(encoding="utf-8", errors="replace")
        return {"ok": True, "conteudo": content[:max_chars], "erro": None}
    except ValueError as e:
        return {"ok": False, "conteudo": "", "erro": str(e)}
    except Exception as e:
        return {"ok": False, "conteudo": "", "erro": str(e)}


def escrever_arquivo_workspace(caminho: str, conteudo: str) -> Dict[str, Any]:
    """Escreve no workspace. Cria backup automático antes de modificar."""
    try:
        sandbox = _get_sandbox()
        target = _safe_path(sandbox, caminho)

        # Backup antes de modificar
        backup_path = None
        if target.exists():
            backup_root = sandbox / BACKUP_DIR
            backup_root.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = caminho.replace("/", "_").replace("\\", "_")
            backup_path = backup_root / f"{safe_name}.{ts}.bak"
            shutil.copy2(target, backup_path)

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(conteudo, encoding="utf-8", errors="replace")
        return {"ok": True, "backup": str(backup_path) if backup_path else None, "erro": None}
    except ValueError as e:
        return {"ok": False, "backup": None, "erro": str(e)}
    except Exception as e:
        return {"ok": False, "backup": None, "erro": str(e)}


def analisar_codigo(codigo: str) -> Dict[str, Any]:
    """
    Detecta vulnerabilidades, más práticas, problemas de arquitetura.
    Retorna: {ok, relatorio, vulnerabilidades, sugestoes}
    """
    if not codigo or not isinstance(codigo, str):
        return {"ok": False, "erro": "Código vazio ou inválido."}

    codigo = codigo.strip()
    if codigo.startswith("```"):
        lines = codigo.split("\n")
        if lines[-1].strip() == "```":
            codigo = "\n".join(lines[1:-1])
        else:
            codigo = "\n".join(lines[1:])

    try:
        from yui_ai.tools.code_analyzer import analisar_codigo as _analisar
        result = _analisar(codigo, {"content": codigo, "filename": "codigo.py"})
        if result.get("ok"):
            return {
                "ok": True,
                "relatorio": result.get("texto", ""),
                "vulnerabilidades": _extrair_vulnerabilidades(result.get("relatorio")),
                "sugestoes": result.get("texto", ""),
            }
        return {
            "ok": False,
            "erro": result.get("erro", "Falha na análise."),
        }
    except Exception as e:
        return {"ok": False, "erro": str(e)}


def _extrair_vulnerabilidades(relatorio: Any) -> list:
    if not relatorio:
        return []
    if isinstance(relatorio, dict):
        problemas = relatorio.get("problemas", []) or relatorio.get("riscos", [])
        return [str(p.get("mensagem", p)) for p in problemas] if problemas else []
    return []


def sugerir_arquitetura(tipo_projeto: str) -> Dict[str, Any]:
    """
    Retorna estrutura ideal de pastas e responsabilidades.
    tipo_projeto: web, api, mobile, fullstack, microsaas, etc.
    """
    tipo = (tipo_projeto or "").strip().lower()
    if not tipo:
        return {"ok": False, "erro": "Informe o tipo de projeto."}

    templates: Dict[str, Dict[str, Any]] = {
        "web": {
            "estrutura": "src/\n  components/\n  pages/\n  styles/\n  utils/\npublic/\nstatic/\npackage.json",
            "responsabilidades": "components: UI reutilizáveis | pages: rotas/views | styles: CSS/SCSS",
        },
        "api": {
            "estrutura": "src/\n  routes/\n  controllers/\n  models/\n  services/\n  middleware/\nconfig/\ntests/",
            "responsabilidades": "routes: endpoints | controllers: lógica HTTP | models: dados | services: regras de negócio",
        },
        "mobile": {
            "estrutura": "src/\n  screens/\n  components/\n  navigation/\n  hooks/\n  services/\nassets/\n",
            "responsabilidades": "screens: telas | components: UI | navigation: rotas | hooks: lógica reutilizável",
        },
        "fullstack": {
            "estrutura": "backend/\n  api/\n  models/\n  services/\nfrontend/\n  src/\n    components/\n    pages/\nshared/\n  types/\n  utils/",
            "responsabilidades": "backend: API e dados | frontend: UI | shared: tipos e utils compartilhados",
        },
        "microsaas": {
            "estrutura": "app/\n  api/\n  auth/\n  dashboard/\n  pages/\nlib/\n  db/\n  auth/\n  billing/\ncomponents/\nprisma/",
            "responsabilidades": "app: Next.js app router | lib: db, auth, billing | components: UI",
        },
        "python": {
            "estrutura": "src/\n  __init__.py\n  main.py\n  app/\n  routes/\n  models/\n  services/\nconfig/\ntests/\nrequirements.txt",
            "responsabilidades": "app: aplicação | routes: endpoints | models: ORM | services: lógica",
        },
    }

    for key, val in templates.items():
        if key in tipo or tipo in key:
            return {
                "ok": True,
                "tipo": tipo,
                "estrutura": val["estrutura"],
                "responsabilidades": val["responsabilidades"],
            }

    return {
        "ok": True,
        "tipo": tipo,
        "estrutura": "src/\n  components/\n  services/\n  utils/\nconfig/\ntests/",
        "responsabilidades": "Estrutura genérica. Especifique: web, api, mobile, fullstack ou microsaas.",
    }


def calcular_custo_estimado(tokens_entrada: int, tokens_saida: int) -> Dict[str, Any]:
    """
    Retorna estimativa de custo em USD e BRL.
    Baseado em gpt-4o-mini: input $0.15/1M, output $0.60/1M
    """
    try:
        from core.usage_tracker import (
            PRICE_INPUT_PER_1M,
            PRICE_OUTPUT_PER_1M,
            BRL_PER_USD,
        )
    except ImportError:
        PRICE_INPUT_PER_1M = 0.15
        PRICE_OUTPUT_PER_1M = 0.60
        BRL_PER_USD = 5.0

    inp = max(0, int(tokens_entrada))
    out = max(0, int(tokens_saida))
    usd = (inp * PRICE_INPUT_PER_1M / 1_000_000) + (out * PRICE_OUTPUT_PER_1M / 1_000_000)
    brl = round(usd * BRL_PER_USD, 4)
    return {
        "ok": True,
        "tokens_entrada": inp,
        "tokens_saida": out,
        "custo_usd": round(usd, 6),
        "custo_brl": brl,
    }


def resumir_contexto(conversa: str) -> Dict[str, Any]:
    """
    Retorna resumo técnico curto para memória.
    Usado quando histórico > 10 mensagens.
    """
    if not conversa or not isinstance(conversa, str):
        return {"ok": False, "erro": "Conversa vazia."}

    conversa = conversa.strip()
    if len(conversa) < 50:
        return {"ok": True, "resumo": conversa[:200]}

    try:
        from openai import OpenAI
        import os
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        if not client.api_key:
            return {"ok": True, "resumo": conversa[:2000] + "..." if len(conversa) > 2000 else conversa}

        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Resuma em 2-4 frases técnicas o essencial desta conversa. Use português."},
                {"role": "user", "content": conversa[:8000]},
            ],
            temperature=0.2,
            max_tokens=200,
        )
        resumo = ""
        if r.choices and len(r.choices) > 0:
            resumo = (r.choices[0].message.content or "").strip()
        return {"ok": True, "resumo": resumo or conversa[:500]}
    except Exception:
        return {"ok": True, "resumo": conversa[:1500] + "..." if len(conversa) > 1500 else conversa}


def executar_tool(nome: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatcher: executa a tool pelo nome."""
    if nome == "analisar_codigo":
        return analisar_codigo(args.get("codigo", "") or "")
    if nome == "sugerir_arquitetura":
        return sugerir_arquitetura(args.get("tipo_projeto", "") or "")
    if nome == "calcular_custo_estimado":
        return calcular_custo_estimado(
            int(args.get("tokens_entrada", 0) or 0),
            int(args.get("tokens_saida", 0) or 0),
        )
    if nome == "resumir_contexto":
        return resumir_contexto(args.get("conversa", "") or "")
    if nome == "listar_arquivos_workspace":
        return listar_arquivos_workspace(args.get("pasta", ".") or ".")
    if nome == "ler_arquivo_workspace":
        return ler_arquivo_workspace(
            args.get("caminho", "") or "",
            int(args.get("max_chars", 8000) or 8000),
        )
    if nome == "escrever_arquivo_workspace":
        return escrever_arquivo_workspace(
            args.get("caminho", "") or "",
            args.get("conteudo", "") or "",
        )
    return {"ok": False, "erro": f"Tool desconhecida: {nome}"}
