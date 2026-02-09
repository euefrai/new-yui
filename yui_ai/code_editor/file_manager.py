"""
Gerenciador de múltiplos arquivos para edição simultânea.
"""

import os
from typing import Dict, List, Optional, Tuple
from yui_ai.code_editor.patch_engine import PatchEngine


class FileManager:
    """
    Gerencia edição de múltiplos arquivos simultaneamente.
    """

    def __init__(self):
        self.patch_engine = PatchEngine()
        self.arquivos_abertos: Dict[str, str] = {}  # caminho -> conteúdo

    def abrir_arquivo(self, caminho: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Abre um arquivo para edição.

        Retorna: (sucesso, conteudo, mensagem_erro)
        """
        caminho_abs = os.path.abspath(caminho)

        if not os.path.exists(caminho_abs):
            return False, None, f"Arquivo não existe: {caminho_abs}"

        try:
            with open(caminho_abs, "r", encoding="utf-8", errors="replace") as f:
                conteudo = f.read()

            self.arquivos_abertos[caminho_abs] = conteudo
            return True, conteudo, None

        except Exception as e:
            return False, None, str(e)

    def fechar_arquivo(self, caminho: str) -> bool:
        """Fecha um arquivo (remove da memória)."""
        caminho_abs = os.path.abspath(caminho)
        if caminho_abs in self.arquivos_abertos:
            del self.arquivos_abertos[caminho_abs]
            return True
        return False

    def preparar_edicao(
        self,
        caminho: str,
        conteudo_novo: str,
        descricao: str = ""
    ) -> Tuple[bool, Optional[dict], Optional[str]]:
        """
        Prepara uma edição sem aplicar ainda.

        Retorna: (sucesso, patch, mensagem_erro)
        """
        caminho_abs = os.path.abspath(caminho)

        # Abre arquivo se não estiver aberto
        if caminho_abs not in self.arquivos_abertos:
            sucesso, conteudo, erro = self.abrir_arquivo(caminho_abs)
            if not sucesso:
                return False, None, erro

        conteudo_antigo = self.arquivos_abertos[caminho_abs]

        try:
            patch = self.patch_engine.preparar_patch(
                caminho_abs,
                conteudo_antigo,
                conteudo_novo,
                descricao
            )
            return True, patch, None

        except Exception as e:
            return False, None, str(e)

    def aplicar_edicao(self, patch: dict, validar: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Aplica uma edição preparada.

        Retorna: (sucesso, mensagem_erro)
        """
        sucesso, erro = self.patch_engine.aplicar_patch(patch, validar)

        if sucesso:
            # Atualiza conteúdo em memória
            caminho_abs = patch["arquivo"]
            self.arquivos_abertos[caminho_abs] = patch["conteudo_novo"]

        return sucesso, erro

    def aplicar_todas_edicoes(self, validar: bool = True) -> List[Tuple[bool, str, Optional[str]]]:
        """
        Aplica todas as edições pendentes.

        Retorna: [(sucesso, arquivo, mensagem_erro), ...]
        """
        resultados = self.patch_engine.aplicar_todos_pendentes(validar)

        # Atualiza conteúdos em memória
        for sucesso, arquivo, _ in resultados:
            if sucesso:
                # Recarrega arquivo atualizado
                self.abrir_arquivo(arquivo)

        return resultados

    def visualizar_mudancas_pendentes(self) -> str:
        """Gera visualização de todas as mudanças pendentes."""
        if not self.patch_engine.patches_pendentes:
            return "Nenhuma mudança pendente."

        linhas = ["📝 Mudanças pendentes:"]
        linhas.append("")

        for patch in self.patch_engine.patches_pendentes:
            linhas.append(self.patch_engine.visualizar_patch(patch))
            linhas.append("")

        return "\n".join(linhas)

    def reverter_edicao(self, patch: dict) -> Tuple[bool, Optional[str]]:
        """
        Reverte uma edição aplicada.

        Retorna: (sucesso, mensagem_erro)
        """
        sucesso, erro = self.patch_engine.reverter_patch(patch)

        if sucesso:
            # Atualiza conteúdo em memória
            caminho_abs = patch["arquivo"]
            self.arquivos_abertos[caminho_abs] = patch["conteudo_antigo"]

        return sucesso, erro

    def obter_historico(self, caminho: Optional[str] = None) -> List[dict]:
        """
        Retorna histórico de edições.

        Se caminho for None, retorna todos.
        """
        caminho_abs = os.path.abspath(caminho) if caminho else None
        return self.patch_engine.obter_historico(caminho_abs)
