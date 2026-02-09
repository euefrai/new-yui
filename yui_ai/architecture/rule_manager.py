"""
Gerenciador de regras do projeto com comandos naturais.
"""

from typing import Dict, List, Optional, Tuple
from yui_ai.architecture.memory_store import ArchitectureMemory


class RuleManager:
    """
    Gerencia registro e consulta de regras de forma natural.
    """

    def __init__(self):
        self.memory = ArchitectureMemory()

    def preparar_registro_regra_natural(
        self,
        texto_comando: str
    ) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Prepara registro de regra a partir de comando natural (NÃO SALVA AINDA).

        Exemplos:
        - "regra: sempre usar type hints em Python"
        - "padrão: funções devem ter docstrings"
        - "restrição: não usar imports globais"

        Retorna: (sucesso, entrada_preparada, mensagem_erro)
        """
        texto = texto_comando.lower().strip()

        # Detecta tipo de registro e prepara entrada (sem salvar)
        if texto.startswith("regra:"):
            conteudo = texto.replace("regra:", "").strip()
            entrada = {
                "regra": conteudo,
                "descricao": "",
                "tipo": "geral",
                "obrigatoria": True,
                "tags": []
            }
            return True, entrada, None

        elif texto.startswith("padrão:") or texto.startswith("padrao:"):
            conteudo = texto.replace("padrão:", "").replace("padrao:", "").strip()
            entrada = {
                "nome": conteudo.split(":")[0] if ":" in conteudo else conteudo,
                "descricao": conteudo,
                "exemplo": "",
                "quando_usar": "",
                "tags": []
            }
            return True, entrada, None

        elif texto.startswith("restrição:") or texto.startswith("restricao:"):
            conteudo = texto.replace("restrição:", "").replace("restricao:", "").strip()
            entrada = {
                "restricao": conteudo,
                "motivo": "",
                "tags": []
            }
            return True, entrada, None

        elif texto.startswith("decisão:") or texto.startswith("decisao:"):
            partes = texto.replace("decisão:", "").replace("decisao:", "").strip().split("motivo:")
            decisao = partes[0].strip()
            motivo = partes[1].strip() if len(partes) > 1 else ""
            entrada = {
                "decisao": decisao,
                "motivo": motivo,
                "contexto": "",
                "tags": []
            }
            return True, entrada, None

        return False, None, "Formato de comando não reconhecido. Use: regra:, padrão:, restrição: ou decisão:"

    def confirmar_registro_regra(self, entrada: Dict, tipo: str) -> Dict:
        """
        Confirma e salva registro de regra/padrão/restrição/decisão.
        """
        if tipo == "regra":
            return self.memory.registrar_regra(
                regra=entrada.get("regra", ""),
                descricao=entrada.get("descricao", ""),
                tipo=entrada.get("tipo", "geral"),
                obrigatoria=entrada.get("obrigatoria", True),
                tags=entrada.get("tags", [])
            )
        elif tipo == "padrão":
            return self.memory.registrar_padrao(
                nome=entrada.get("nome", ""),
                descricao=entrada.get("descricao", ""),
                exemplo=entrada.get("exemplo", ""),
                quando_usar=entrada.get("quando_usar", ""),
                tags=entrada.get("tags", [])
            )
        elif tipo == "restrição":
            return self.memory.registrar_restricao(
                restricao=entrada.get("restricao", ""),
                motivo=entrada.get("motivo", ""),
                tags=entrada.get("tags", [])
            )
        elif tipo == "decisão":
            return self.memory.registrar_decisao(
                decisao=entrada.get("decisao", ""),
                motivo=entrada.get("motivo", ""),
                contexto=entrada.get("contexto", ""),
                tags=entrada.get("tags", [])
            )
        else:
            raise ValueError(f"Tipo desconhecido: {tipo}")

    def consultar_regras(
        self,
        filtro: str = ""
    ) -> List[Dict]:
        """
        Consulta regras com filtro opcional.
        """
        if filtro:
            # Tenta filtrar por tags ou conteúdo
            tags = [t.strip() for t in filtro.split(",")]
            return self.memory.obter_regras_relevantes(tags=tags)
        return self.memory.obter_regras_relevantes()

    def consultar_padroes(
        self,
        filtro: str = ""
    ) -> List[Dict]:
        """Consulta padrões arquiteturais."""
        if filtro:
            tags = [t.strip() for t in filtro.split(",")]
            return self.memory.obter_padroes_relevantes(tags=tags)
        return self.memory.obter_padroes_relevantes()

    def consultar_tudo(
        self,
        tipo: Optional[str] = None
    ) -> Dict:
        """
        Consulta toda a memória arquitetural.

        tipo: "regras", "padroes", "decisoes", "restricoes" ou None para tudo
        """
        tudo = self.memory.obter_tudo()

        if tipo == "regras":
            return {"regras": tudo.get("regras", [])}
        elif tipo == "padroes":
            return {"padroes": tudo.get("padroes_arquiteturais", [])}
        elif tipo == "decisoes":
            return {"decisoes": tudo.get("decisoes_tecnicas", [])}
        elif tipo == "restricoes":
            return {"restricoes": tudo.get("restricoes", [])}

        return tudo

    def formatar_regras_para_exibicao(self, regras: List[Dict]) -> str:
        """Formata regras para exibição legível."""
        if not regras:
            return "Nenhuma regra registrada."

        linhas = ["📋 REGRAS DO PROJETO:"]
        linhas.append("")

        for regra in regras:
            obrigatoria = "🔴 OBRIGATÓRIA" if regra.get("obrigatoria", True) else "🟡 Opcional"
            linhas.append(f"  {obrigatoria}: {regra['regra']}")
            if regra.get("descricao"):
                linhas.append(f"    {regra['descricao']}")
            linhas.append("")

        return "\n".join(linhas)

    def formatar_padroes_para_exibicao(self, padroes: List[Dict]) -> str:
        """Formata padrões para exibição legível."""
        if not padroes:
            return "Nenhum padrão registrado."

        linhas = ["🏗️ PADRÕES ARQUITETURAIS:"]
        linhas.append("")

        for padrao in padroes:
            linhas.append(f"  • {padrao['nome']}")
            linhas.append(f"    {padrao['descricao']}")
            if padrao.get("quando_usar"):
                linhas.append(f"    Quando usar: {padrao['quando_usar']}")
            linhas.append("")

        return "\n".join(linhas)
