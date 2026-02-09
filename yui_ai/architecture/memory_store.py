"""
Armazenamento persistente de memória arquitetural.
"""

import os
import json
from typing import Dict, List, Optional
from datetime import datetime
from yui_ai.memory.memory import BASE_DATA_DIR


ARCHITECTURE_FILE = os.path.join(BASE_DATA_DIR, "architecture_memory.json")


class ArchitectureMemory:
    """
    Gerencia memória arquitetural persistente do projeto.
    """

    def __init__(self):
        self.memoria: Dict = self._carregar_memoria()

    def _estrutura_base(self) -> Dict:
        """Retorna estrutura base da memória arquitetural."""
        return {
            "projeto": {
                "nome": "",
                "linguagem": "",
                "versao_linguagem": "",
                "framework": "",
                "descricao": ""
            },
            "decisoes_tecnicas": [],
            "padroes_arquiteturais": [],
            "regras": [],
            "restricoes": [],
            "convencoes": {
                "nomenclatura": {},
                "estrutura": {},
                "documentacao": {}
            },
            "historico_mudancas": []
        }

    def _carregar_memoria(self) -> Dict:
        """Carrega memória do disco."""
        if not os.path.exists(ARCHITECTURE_FILE):
            memoria = self._estrutura_base()
            self._salvar_memoria(memoria)
            return memoria

        try:
            with open(ARCHITECTURE_FILE, "r", encoding="utf-8") as f:
                memoria = json.load(f)
            
            # Garante estrutura completa
            base = self._estrutura_base()
            for chave, valor in base.items():
                if chave not in memoria:
                    memoria[chave] = valor
                elif isinstance(valor, dict) and isinstance(memoria.get(chave), dict):
                    for subchave, subvalor in valor.items():
                        if subchave not in memoria[chave]:
                            memoria[chave][subchave] = subvalor

            return memoria
        except Exception:
            memoria = self._estrutura_base()
            self._salvar_memoria(memoria)
            return memoria

    def _salvar_memoria(self, memoria: Optional[Dict] = None):
        """Salva memória no disco."""
        if memoria is None:
            memoria = self.memoria

        try:
            os.makedirs(os.path.dirname(ARCHITECTURE_FILE), exist_ok=True)
            with open(ARCHITECTURE_FILE, "w", encoding="utf-8") as f:
                json.dump(memoria, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ Erro ao salvar memória arquitetural: {e}")

    def registrar_decisao(
        self,
        decisao: str,
        motivo: str = "",
        contexto: str = "",
        tags: List[str] = None
    ) -> Dict:
        """
        Registra uma decisão técnica.

        Retorna: entrada registrada
        """
        entrada = {
            "id": len(self.memoria["decisoes_tecnicas"]),
            "decisao": decisao,
            "motivo": motivo,
            "contexto": contexto,
            "tags": tags or [],
            "timestamp": datetime.now().isoformat()
        }

        self.memoria["decisoes_tecnicas"].append(entrada)
        self._salvar_memoria()

        return entrada

    def registrar_padrao(
        self,
        nome: str,
        descricao: str,
        exemplo: str = "",
        quando_usar: str = "",
        tags: List[str] = None
    ) -> Dict:
        """
        Registra um padrão arquitetural.

        Retorna: entrada registrada
        """
        entrada = {
            "id": len(self.memoria["padroes_arquiteturais"]),
            "nome": nome,
            "descricao": descricao,
            "exemplo": exemplo,
            "quando_usar": quando_usar,
            "tags": tags or [],
            "timestamp": datetime.now().isoformat()
        }

        self.memoria["padroes_arquiteturais"].append(entrada)
        self._salvar_memoria()

        return entrada

    def registrar_regra(
        self,
        regra: str,
        descricao: str = "",
        tipo: str = "geral",  # geral, nomenclatura, estrutura, segurança
        obrigatoria: bool = True,
        tags: List[str] = None
    ) -> Dict:
        """
        Registra uma regra do projeto.

        Retorna: entrada registrada
        """
        entrada = {
            "id": len(self.memoria["regras"]),
            "regra": regra,
            "descricao": descricao,
            "tipo": tipo,
            "obrigatoria": obrigatoria,
            "tags": tags or [],
            "timestamp": datetime.now().isoformat()
        }

        self.memoria["regras"].append(entrada)
        self._salvar_memoria()

        return entrada

    def registrar_restricao(
        self,
        restricao: str,
        motivo: str = "",
        tags: List[str] = None
    ) -> Dict:
        """
        Registra uma restrição arquitetural.

        Retorna: entrada registrada
        """
        entrada = {
            "id": len(self.memoria["restricoes"]),
            "restricao": restricao,
            "motivo": motivo,
            "tags": tags or [],
            "timestamp": datetime.now().isoformat()
        }

        self.memoria["restricoes"].append(entrada)
        self._salvar_memoria()

        return entrada

    def obter_regras_relevantes(
        self,
        contexto: str = "",
        tags: List[str] = None
    ) -> List[Dict]:
        """
        Retorna regras relevantes para um contexto.

        Filtra por tags e contexto se fornecidos.
        """
        regras = self.memoria.get("regras", [])

        if tags:
            regras = [
                r for r in regras
                if any(tag in r.get("tags", []) for tag in tags)
            ]

        # Ordena por obrigatoriedade primeiro
        regras.sort(key=lambda x: (not x.get("obrigatoria", True), x.get("id", 0)))

        return regras

    def obter_padroes_relevantes(
        self,
        contexto: str = "",
        tags: List[str] = None
    ) -> List[Dict]:
        """
        Retorna padrões relevantes para um contexto.
        """
        padroes = self.memoria.get("padroes_arquiteturais", [])

        if tags:
            padroes = [
                p for p in padroes
                if any(tag in p.get("tags", []) for tag in tags)
            ]

        return padroes

    def obter_decisoes_relevantes(
        self,
        contexto: str = "",
        tags: List[str] = None
    ) -> List[Dict]:
        """
        Retorna decisões técnicas relevantes.
        """
        decisoes = self.memoria.get("decisoes_tecnicas", [])

        if tags:
            decisoes = [
                d for d in decisoes
                if any(tag in d.get("tags", []) for tag in tags)
            ]

        return decisoes

    def obter_restricoes_relevantes(
        self,
        contexto: str = "",
        tags: List[str] = None
    ) -> List[Dict]:
        """
        Retorna restrições relevantes.
        """
        restricoes = self.memoria.get("restricoes", [])

        if tags:
            restricoes = [
                r for r in restricoes
                if any(tag in r.get("tags", []) for tag in tags)
            ]

        return restricoes

    def montar_contexto_arquitetural(
        self,
        arquivo: str = "",
        contexto_operacao: str = ""
    ) -> str:
        """
        Monta contexto arquitetural para incluir em prompts da IA.

        Retorna: string formatada com regras, padrões e decisões relevantes.
        """
        linhas = []

        # Informações do projeto
        projeto = self.memoria.get("projeto", {})
        if projeto.get("linguagem"):
            linhas.append(f"Linguagem: {projeto['linguagem']}")
            if projeto.get("versao_linguagem"):
                linhas.append(f"Versão: {projeto['versao_linguagem']}")
            if projeto.get("framework"):
                linhas.append(f"Framework: {projeto['framework']}")

        # Regras obrigatórias
        regras_obrigatorias = [
            r for r in self.memoria.get("regras", [])
            if r.get("obrigatoria", True)
        ]
        if regras_obrigatorias:
            linhas.append("\nREGRAS OBRIGATÓRIAS DO PROJETO:")
            for regra in regras_obrigatorias[:10]:  # Limita a 10
                linhas.append(f"- {regra['regra']}")
                if regra.get("descricao"):
                    linhas.append(f"  {regra['descricao']}")

        # Padrões arquiteturais
        padroes = self.memoria.get("padroes_arquiteturais", [])
        if padroes:
            linhas.append("\nPADRÕES ARQUITETURAIS:")
            for padrao in padroes[:5]:  # Limita a 5
                linhas.append(f"- {padrao['nome']}: {padrao['descricao']}")

        # Restrições
        restricoes = self.memoria.get("restricoes", [])
        if restricoes:
            linhas.append("\nRESTRIÇÕES:")
            for restricao in restricoes[:5]:  # Limita a 5
                linhas.append(f"- {restricao['restricao']}")
                if restricao.get("motivo"):
                    linhas.append(f"  Motivo: {restricao['motivo']}")

        # Decisões técnicas recentes
        decisoes = self.memoria.get("decisoes_tecnicas", [])
        if decisoes:
            linhas.append("\nDECISÕES TÉCNICAS RECENTES:")
            for decisao in decisoes[-3:]:  # Últimas 3
                linhas.append(f"- {decisao['decisao']}")
                if decisao.get("motivo"):
                    linhas.append(f"  Motivo: {decisao['motivo']}")

        return "\n".join(linhas)

    def atualizar_info_projeto(
        self,
        nome: str = None,
        linguagem: str = None,
        versao_linguagem: str = None,
        framework: str = None,
        descricao: str = None
    ):
        """Atualiza informações básicas do projeto."""
        projeto = self.memoria.get("projeto", {})

        if nome is not None:
            projeto["nome"] = nome
        if linguagem is not None:
            projeto["linguagem"] = linguagem
        if versao_linguagem is not None:
            projeto["versao_linguagem"] = versao_linguagem
        if framework is not None:
            projeto["framework"] = framework
        if descricao is not None:
            projeto["descricao"] = descricao

        self.memoria["projeto"] = projeto
        self._salvar_memoria()

    def obter_tudo(self) -> Dict:
        """Retorna toda a memória arquitetural."""
        return self.memoria.copy()
