"""
Ações de edição de código usando o engine de diff/patch.

TODAS as ações aqui requerem confirmação explícita do usuário.
"""

import os
from yui_ai.code_editor.file_manager import FileManager
from yui_ai.code_editor.history_manager import HistoryManager
from yui_ai.actions.actions import sucesso, falha

# Instância global do FileManager (singleton)
_file_manager = None
_history_manager = None


def _obter_file_manager():
    """Retorna instância singleton do FileManager."""
    global _file_manager
    if _file_manager is None:
        _file_manager = FileManager()
    return _file_manager


def _obter_history_manager():
    """Retorna instância singleton do HistoryManager."""
    global _history_manager
    if _history_manager is None:
        _history_manager = HistoryManager()
    return _history_manager


def preparar_edicao_codigo(arquivo: str, conteudo_novo: str, descricao: str = "") -> dict:
    """
    Prepara uma edição de código SEM APLICAR.

    Retorna: {
        "ok": bool,
        "mensagem": str,
        "codigo": str,
        "dados": {
            "patch": dict,  # patch preparado
            "visualizacao": str,  # visualização das mudanças
            "arquivo": str
        }
    }
    """
    arquivo_abs = os.path.abspath(arquivo)

    if not os.path.exists(arquivo_abs):
        return falha(f"Arquivo não encontrado: {arquivo_abs}", "ARQUIVO_NAO_EXISTE")

    if os.path.isdir(arquivo_abs):
        return falha(f"Caminho é uma pasta, não um arquivo: {arquivo_abs}", "NAO_E_ARQUIVO")

    try:
        fm = _obter_file_manager()
        sucesso_prep, patch, erro = fm.preparar_edicao(
            arquivo_abs,
            conteudo_novo,
            descricao or f"Edição em {os.path.basename(arquivo_abs)}"
        )

        if not sucesso_prep:
            return falha(erro or "Falha ao preparar edição", "ERRO_PREPARAR_EDICAO")

        visualizacao = fm.visualizar_mudancas_pendentes()

        return sucesso(
            "Edição preparada (aguardando confirmação)",
            {
                "patch": patch,
                "visualizacao": visualizacao,
                "arquivo": arquivo_abs
            }
        )

    except Exception as e:
        return falha(str(e), "ERRO_CRITICO_EDICAO")


def aplicar_edicao_codigo(patch: dict, validar: bool = True) -> dict:
    """
    Aplica uma edição de código preparada.

    Retorna: {
        "ok": bool,
        "mensagem": str,
        "codigo": str,
        "dados": {
            "arquivo": str,
            "entrada_historico": dict  # entrada registrada no histórico
        }
    }
    """
    try:
        fm = _obter_file_manager()
        hm = _obter_history_manager()

        arquivo = patch["arquivo"]

        # Aplica edição
        sucesso_aplicar, erro = fm.aplicar_edicao(patch, validar)

        if not sucesso_aplicar:
            return falha(erro or "Falha ao aplicar edição", "ERRO_APLICAR_EDICAO")

        # Registra no histórico
        entrada_historico = hm.registrar_mudanca(
            arquivo,
            patch["conteudo_antigo"],
            patch["conteudo_novo"],
            patch.get("descricao", ""),
            tags=["edicao_codigo"]
        )

        return sucesso(
            f"Edição aplicada em {os.path.basename(arquivo)}",
            {
                "arquivo": arquivo,
                "entrada_historico": entrada_historico
            }
        )

    except Exception as e:
        return falha(str(e), "ERRO_CRITICO_APLICAR")


def visualizar_edicoes_pendentes() -> dict:
    """
    Retorna visualização de todas as edições pendentes.
    """
    try:
        fm = _obter_file_manager()
        visualizacao = fm.visualizar_mudancas_pendentes()

        return sucesso(
            "Visualização de edições pendentes",
            {"visualizacao": visualizacao}
        )

    except Exception as e:
        return falha(str(e), "ERRO_VISUALIZAR")


def reverter_edicao_codigo(arquivo: str, entrada_id: int = None) -> dict:
    """
    Reverte uma edição aplicada.

    Se entrada_id for None, reverte a última edição do arquivo.
    """
    try:
        hm = _obter_history_manager()
        arquivo_abs = os.path.abspath(arquivo)

        if entrada_id is None:
            # Reverte última edição
            sucesso_rev, erro = hm.reverter_arquivo(arquivo_abs)
        else:
            # Reverte edição específica
            sucesso_rev, erro = hm.reverter_mudanca(entrada_id)

        if not sucesso_rev:
            return falha(erro or "Falha ao reverter edição", "ERRO_REVERTER")

        return sucesso(
            f"Edição revertida em {os.path.basename(arquivo_abs)}",
            {"arquivo": arquivo_abs}
        )

    except Exception as e:
        return falha(str(e), "ERRO_CRITICO_REVERTER")


def obter_historico_edicoes(arquivo: str = None, limite: int = 10) -> dict:
    """
    Retorna histórico de edições.

    Se arquivo for None, retorna histórico geral.
    """
    try:
        hm = _obter_history_manager()
        historico = hm.obter_historico(arquivo, limite)

        return sucesso(
            "Histórico de edições",
            {
                "historico": historico,
                "total": len(historico)
            }
        )

    except Exception as e:
        return falha(str(e), "ERRO_HISTORICO")
