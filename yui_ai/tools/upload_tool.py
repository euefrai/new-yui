# ============================================================
# UPLOAD TOOL - YUI
# Recebe menção a upload/envio de arquivo (uso via interface ou contexto)
# ============================================================

from typing import Any, Dict, Optional


def executar_upload(mensagem: str, contexto: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Trata intenção de upload. Em contexto web o arquivo vem pelo request;
    aqui devolve instrução ou resultado se contexto tiver dados do arquivo.
    """
    contexto = contexto or {}
    conteudo = contexto.get("content") or contexto.get("conteudo")
    filename = contexto.get("filename") or contexto.get("arquivo") or "arquivo.txt"
    if conteudo is not None:
        if isinstance(conteudo, bytes):
            conteudo = conteudo.decode("utf-8", errors="ignore")
        return {
            "status": "recebido",
            "arquivo": filename,
            "tamanho": len(conteudo),
            "mensagem": "Use 'analisa esse código' ou a análise de arquivo para avaliar o conteúdo.",
        }
    return {
        "status": "instrucao",
        "mensagem": "Envie o arquivo pela interface do chat (arrastar ou anexar). Depois peça: analisa esse código.",
    }
