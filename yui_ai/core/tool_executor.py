# ============================================================
# TOOL EXECUTOR AGENT - YUI
# Decide automaticamente se deve chamar uma tool a partir da intenção
# ============================================================

from typing import Any, Callable, Dict, Optional

from yui_ai.core.intent_parser import interpretar_intencao
from yui_ai.tools.upload_tool import executar_upload
from yui_ai.tools.code_analyzer import analisar_codigo


def _resolve_tool_name(intencao: Dict[str, Any], mensagem: str) -> Optional[str]:
    """
    Mapeia resultado do intent_parser + mensagem para nome da tool.
    intent_parser retorna dict com tipo, acao, dados; aqui derivamos 'upload' ou 'analisar_codigo'.
    """
    msg = (mensagem or "").lower().strip()
    tipo = intencao.get("tipo")
    acao = intencao.get("acao")

    # Upload: palavras-chave na mensagem
    if any(p in msg for p in ("upload", "envia arquivo", "enviar arquivo", "anexa arquivo", "anexar arquivo")):
        return "upload"

    # Análise de código: mensagem ou ação do intent
    if acao == "analisar_projeto":
        return "analisar_projeto"
    if any(p in msg for p in ("analisa esse", "analise esse", "analisa este", "analise este")):
        return "analisar_codigo"
    if "analisa" in msg and any(p in msg for p in ("código", "codigo", "código", "arquivo")):
        return "analisar_codigo"

    return None


class ToolExecutorAgent:
    def __init__(self) -> None:
        self.tools: Dict[str, Callable[..., Any]] = {
            "upload": executar_upload,
            "analisar_codigo": analisar_codigo,
            "analisar_projeto": self._tool_analisar_projeto,
        }

    def _tool_analisar_projeto(self, mensagem: str, contexto: Optional[Dict[str, Any]] = None) -> Any:
        """Encaminha para a análise de projeto existente."""
        try:
            from yui_ai.project_analysis.analysis_report import executar_analise_completa, formatar_relatorio

            raiz = (contexto or {}).get("raiz") or ""
            ok, relatorio, err = executar_analise_completa(raiz)
            if ok and relatorio:
                return {"ok": True, "texto": formatar_relatorio(relatorio), "relatorio": relatorio}
            return {"ok": False, "erro": err or "Falha na análise.", "texto": None}
        except Exception as e:
            return {"ok": False, "erro": str(e), "texto": None}

    def executar(
        self,
        mensagem_usuario: str,
        contexto: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Decide automaticamente se deve chamar uma tool.
        Retorna dict com status ('chat' | 'tool_executada' | 'erro'), resposta, tool_usada, resultado.
        """
        intencao = interpretar_intencao(mensagem_usuario)
        print(f"[YUI TOOL AGENT] Intenção detectada: {intencao}")

        tool_name = _resolve_tool_name(intencao, mensagem_usuario)
        if tool_name:
            return self._executar_tool(tool_name, mensagem_usuario, contexto or {})

        return {
            "status": "chat",
            "resposta": None,
            "tool_usada": None,
        }

    def _executar_tool(
        self,
        nome_tool: str,
        mensagem: str,
        contexto: Dict[str, Any],
    ) -> Dict[str, Any]:
        tool = self.tools.get(nome_tool)
        if not tool:
            return {
                "status": "erro",
                "mensagem": f"Tool '{nome_tool}' não encontrada.",
            }
        try:
            resultado = tool(mensagem, contexto)
            return {
                "status": "tool_executada",
                "tool_usada": nome_tool,
                "resultado": resultado,
            }
        except Exception as e:
            return {
                "status": "erro",
                "mensagem": str(e),
            }
