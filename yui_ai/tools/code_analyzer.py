# ============================================================
# CODE ANALYZER TOOL - YUI
# Analisa código (conteúdo ou arquivo) usando o pipeline do analyzer
# ============================================================

from typing import Any, Dict


def analisar_codigo(mensagem: str, contexto: dict | None = None) -> Dict[str, Any]:
    """
    Executa análise estática de código. Aceita conteúdo no contexto
    (content + filename) ou extrai da mensagem quando possível.
    """
    contexto = contexto or {}
    content = contexto.get("content") or contexto.get("conteudo")
    filename = contexto.get("filename") or contexto.get("arquivo") or "codigo.py"

    if content is None and mensagem and mensagem.strip():
        # Tenta usar a própria mensagem como código (ex.: usuário colou no chat)
        content = mensagem.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lang = lines[0].replace("```", "").strip() or "py"
                ext = {"py": ".py", "js": ".js", "ts": ".ts"}.get(lang.lower(), ".py")
            else:
                ext = ".py"
            if lines[-1].strip() == "```":
                content = "\n".join(lines[1:-1])
            else:
                content = "\n".join(lines[1:])
            filename = f"codigo{ext}"

    if not content:
        return {
            "ok": False,
            "erro": "Nenhum código para analisar. Cole o código na mensagem ou envie um arquivo.",
            "relatorio": None,
        }

    if isinstance(content, str):
        content = content.encode("utf-8", errors="ignore")

    try:
        from yui_ai.analyzer.report_formatter import run_file_analysis, report_to_text

        ok, report, err = run_file_analysis(content, filename)
        if not ok or report is None:
            return {
                "ok": False,
                "erro": err or "Falha na análise.",
                "relatorio": None,
            }
        texto = report_to_text(report)
        return {
            "ok": True,
            "erro": None,
            "relatorio": report,
            "texto": texto,
        }
    except Exception as e:
        return {
            "ok": False,
            "erro": str(e),
            "relatorio": None,
        }
