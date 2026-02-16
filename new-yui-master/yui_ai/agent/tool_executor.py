# =============================================================
# ToolExecutor — executa ferramentas por intenção (upload, análise, etc.)
# Expansível: adicionar novos intents e delegar às tools reais.
# =============================================================

from typing import Any, Dict, Optional


class ToolExecutor:
    def execute(self, intent: str, payload: Any) -> Optional[Dict[str, Any]]:
        if intent == "upload":
            return {"status": "ok", "tool": "upload", "message": "Use o botão de anexo (📎) para enviar o arquivo."}
        if intent == "code_analysis":
            return {"status": "ok", "tool": "analysis", "message": "Envie um arquivo para análise ou cole o código na mensagem."}
        return None


executor = ToolExecutor()
