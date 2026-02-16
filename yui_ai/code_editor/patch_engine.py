"""
Engine de aplicação de patches com validação e rollback.
"""

import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from yui_ai.code_editor.diff_engine import gerar_diff, aplicar_diff, visualizar_diff


class PatchEngine:
    """
    Gerencia aplicação de patches em arquivos com validação e histórico.
    """

    def __init__(self):
        self.patches_pendentes: List[dict] = []
        self.historico: List[dict] = []

    def preparar_patch(
        self,
        arquivo: str,
        conteudo_antigo: str,
        conteudo_novo: str,
        descricao: str = ""
    ) -> dict:
        """
        Prepara um patch sem aplicar ainda.

        Retorna: {
            "arquivo": str,
            "hunks": List[dict],
            "descricao": str,
            "timestamp": str,
            "conteudo_antigo": str,  # backup
            "conteudo_novo": str
        }
        """
        if not os.path.exists(arquivo):
            raise FileNotFoundError(f"Arquivo não encontrado: {arquivo}")

        hunks = gerar_diff(conteudo_antigo, conteudo_novo, arquivo)

        patch = {
            "arquivo": arquivo,
            "hunks": hunks,
            "descricao": descricao or f"Modificação em {os.path.basename(arquivo)}",
            "timestamp": datetime.now().isoformat(),
            "conteudo_antigo": conteudo_antigo,
            "conteudo_novo": conteudo_novo,
            "aplicado": False
        }

        self.patches_pendentes.append(patch)
        return patch

    def visualizar_patch(self, patch: dict) -> str:
        """Gera visualização legível do patch."""
        return visualizar_diff(patch["hunks"], patch["arquivo"])

    def aplicar_patch(self, patch: dict, validar: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Aplica um patch em um arquivo.

        Retorna: (sucesso, mensagem_erro)
        """
        arquivo = patch["arquivo"]

        if not os.path.exists(arquivo):
            return False, f"Arquivo não existe: {arquivo}"

        try:
            # Lê conteúdo atual
            with open(arquivo, "r", encoding="utf-8", errors="replace") as f:
                conteudo_atual = f.read()

            # Validação: verifica se o arquivo não mudou desde a preparação
            if validar and conteudo_atual != patch["conteudo_antigo"]:
                return False, (
                    f"Arquivo foi modificado desde a preparação do patch. "
                    f"Conteúdo atual diferente do esperado."
                )

            # Aplica diff
            conteudo_modificado, sucesso = aplicar_diff(
                patch["conteudo_antigo"],
                patch["hunks"]
            )

            if not sucesso:
                return False, "Falha ao aplicar diff (contexto não bateu)"

            # Validação: verifica se resultado bate com o esperado
            if validar and conteudo_modificado != patch["conteudo_novo"]:
                return False, "Resultado da aplicação não bate com o esperado"

            # Escreve arquivo
            with open(arquivo, "w", encoding="utf-8") as f:
                f.write(conteudo_modificado)

            patch["aplicado"] = True
            patch["timestamp_aplicacao"] = datetime.now().isoformat()
            self.historico.append(patch.copy())

            return True, None

        except Exception as e:
            return False, str(e)

    def reverter_patch(self, patch: dict) -> Tuple[bool, Optional[str]]:
        """
        Reverte um patch aplicado (restaura conteúdo antigo).
        """
        arquivo = patch["arquivo"]

        if not patch.get("aplicado"):
            return False, "Patch não foi aplicado ainda"

        try:
            with open(arquivo, "w", encoding="utf-8") as f:
                f.write(patch["conteudo_antigo"])

            patch["aplicado"] = False
            patch["timestamp_reversao"] = datetime.now().isoformat()

            return True, None

        except Exception as e:
            return False, str(e)

    def aplicar_todos_pendentes(self, validar: bool = True) -> List[Tuple[bool, str, Optional[str]]]:
        """
        Aplica todos os patches pendentes.

        Retorna: [(sucesso, arquivo, mensagem_erro), ...]
        """
        resultados = []

        for patch in self.patches_pendentes[:]:
            sucesso, erro = self.aplicar_patch(patch, validar)
            resultados.append((sucesso, patch["arquivo"], erro))

            if sucesso:
                self.patches_pendentes.remove(patch)

        return resultados

    def limpar_pendentes(self):
        """Remove todos os patches pendentes sem aplicar."""
        self.patches_pendentes.clear()

    def obter_historico(self, arquivo: Optional[str] = None) -> List[dict]:
        """
        Retorna histórico de patches aplicados.

        Se arquivo for None, retorna todos.
        """
        if arquivo:
            return [p for p in self.historico if p["arquivo"] == arquivo]
        return self.historico.copy()
