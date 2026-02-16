"""
Gerenciador de histórico completo de mudanças com rollback granular.
"""

import os
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from yui_ai.memory.memory import BASE_DATA_DIR


HISTORY_FILE = os.path.join(BASE_DATA_DIR, "code_history.json")


class HistoryManager:
    """
    Gerencia histórico completo de mudanças de código com rollback.
    """

    def __init__(self):
        self.historico: List[dict] = self._carregar_historico()

    def _carregar_historico(self) -> List[dict]:
        """Carrega histórico do disco."""
        if not os.path.exists(HISTORY_FILE):
            return []

        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _salvar_historico(self):
        """Salva histórico no disco."""
        try:
            os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.historico, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ Erro ao salvar histórico: {e}")

    def registrar_mudanca(
        self,
        arquivo: str,
        conteudo_antigo: str,
        conteudo_novo: str,
        descricao: str = "",
        tags: List[str] = None
    ) -> dict:
        """
        Registra uma mudança no histórico.

        Retorna: entrada do histórico
        """
        entrada = {
            "id": len(self.historico),
            "arquivo": os.path.abspath(arquivo),
            "timestamp": datetime.now().isoformat(),
            "descricao": descricao or f"Modificação em {os.path.basename(arquivo)}",
            "conteudo_antigo": conteudo_antigo,
            "conteudo_novo": conteudo_novo,
            "tags": tags or [],
            "revertido": False
        }

        self.historico.append(entrada)
        self._salvar_historico()

        return entrada

    def obter_historico(
        self,
        arquivo: Optional[str] = None,
        limite: int = 50
    ) -> List[dict]:
        """
        Retorna histórico de mudanças.

        Se arquivo for None, retorna todos.
        """
        historico_filtrado = self.historico

        if arquivo:
            arquivo_abs = os.path.abspath(arquivo)
            historico_filtrado = [
                e for e in self.historico
                if e["arquivo"] == arquivo_abs and not e.get("revertido", False)
            ]

        return historico_filtrado[-limite:]

    def reverter_mudanca(self, entrada_id: int) -> Tuple[bool, Optional[str]]:
        """
        Reverte uma mudança específica.

        Retorna: (sucesso, mensagem_erro)
        """
        if entrada_id < 0 or entrada_id >= len(self.historico):
            return False, "ID de entrada inválido"

        entrada = self.historico[entrada_id]

        if entrada.get("revertido"):
            return False, "Mudança já foi revertida"

        arquivo = entrada["arquivo"]

        if not os.path.exists(arquivo):
            return False, f"Arquivo não existe: {arquivo}"

        try:
            # Restaura conteúdo antigo
            with open(arquivo, "w", encoding="utf-8") as f:
                f.write(entrada["conteudo_antigo"])

            entrada["revertido"] = True
            entrada["timestamp_reversao"] = datetime.now().isoformat()
            self._salvar_historico()

            return True, None

        except Exception as e:
            return False, str(e)

    def reverter_arquivo(self, arquivo: str, para_versao: Optional[int] = None) -> Tuple[bool, Optional[str]]:
        """
        Reverte um arquivo para uma versão anterior.

        Se para_versao for None, reverte para a última versão antes da atual.
        """
        arquivo_abs = os.path.abspath(arquivo)
        historico_arquivo = [
            e for e in self.historico
            if e["arquivo"] == arquivo_abs and not e.get("revertido", False)
        ]

        if not historico_arquivo:
            return False, "Nenhuma mudança encontrada para este arquivo"

        if para_versao is None:
            # Reverte para a última versão antes da atual
            entrada = historico_arquivo[-1]
        else:
            # Reverte para versão específica
            if para_versao < 0 or para_versao >= len(historico_arquivo):
                return False, "Versão inválida"
            entrada = historico_arquivo[para_versao]

        return self.reverter_mudanca(entrada["id"])

    def buscar_por_tags(self, tags: List[str]) -> List[dict]:
        """Busca mudanças por tags."""
        return [
            e for e in self.historico
            if any(tag in e.get("tags", []) for tag in tags)
            and not e.get("revertido", False)
        ]

    def limpar_historico_antigo(self, dias: int = 30):
        """
        Remove entradas do histórico mais antigas que X dias.
        """
        from datetime import timedelta
        limite = datetime.now() - timedelta(days=dias)

        self.historico = [
            e for e in self.historico
            if datetime.fromisoformat(e["timestamp"]) > limite
        ]

        self._salvar_historico()
