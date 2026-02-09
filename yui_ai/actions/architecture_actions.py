"""
Ações relacionadas à memória arquitetural e regras do projeto.
"""

from yui_ai.architecture.rule_manager import RuleManager
from yui_ai.actions.actions import sucesso, falha

# Instância singleton
_rule_manager = None


def _obter_rule_manager():
    """Retorna instância singleton do RuleManager."""
    global _rule_manager
    if _rule_manager is None:
        _rule_manager = RuleManager()
    return _rule_manager


def registrar_regra_arquitetural(comando_completo: str, tipo: str = "", conteudo: str = "") -> dict:
    """
    Prepara registro de regra/padrão/restrição/decisão arquitetural.

    NÃO SALVA - apenas prepara para confirmação.
    """
    try:
        rm = _obter_rule_manager()
        sucesso_prep, entrada, erro = rm.preparar_registro_regra_natural(comando_completo)

        if sucesso_prep:
            # Detecta tipo a partir do comando
            comando_lower = comando_completo.lower()
            tipo_entrada = "regra"
            if "padrão" in comando_lower or "padrao" in comando_lower:
                tipo_entrada = "padrão"
            elif "restrição" in comando_lower or "restricao" in comando_lower:
                tipo_entrada = "restrição"
            elif "decisão" in comando_lower or "decisao" in comando_lower:
                tipo_entrada = "decisão"

            return sucesso(
                f"{tipo_entrada.capitalize()} preparada (aguardando confirmação para salvar)",
                {
                    "entrada": entrada,
                    "tipo": tipo_entrada,
                    "comando": comando_completo
                }
            )
        else:
            return falha(erro or "Falha ao preparar registro", "ERRO_PREPARAR_REGISTRO")

    except Exception as e:
        return falha(str(e), "ERRO_CRITICO_PREPARAR")


def confirmar_registro_regra(entrada: dict, tipo: str) -> dict:
    """
    Confirma e salva registro de regra/padrão/restrição/decisão.
    """
    try:
        rm = _obter_rule_manager()
        entrada_salva = rm.confirmar_registro_regra(entrada, tipo)

        return sucesso(
            f"{tipo.capitalize()} salva na memória arquitetural",
            {
                "entrada": entrada_salva,
                "tipo": tipo
            }
        )

    except Exception as e:
        return falha(str(e), "ERRO_CONFIRMAR_REGISTRO")


def consultar_regras(filtro: str = "") -> dict:
    """
    Consulta regras do projeto.
    """
    try:
        rm = _obter_rule_manager()
        regras = rm.consultar_regras(filtro)
        visualizacao = rm.formatar_regras_para_exibicao(regras)

        return sucesso(
            "Regras do projeto",
            {
                "regras": regras,
                "visualizacao": visualizacao,
                "total": len(regras)
            }
        )

    except Exception as e:
        return falha(str(e), "ERRO_CONSULTAR_REGRA")


def consultar_padroes(filtro: str = "") -> dict:
    """
    Consulta padrões arquiteturais do projeto.
    """
    try:
        rm = _obter_rule_manager()
        padroes = rm.consultar_padroes(filtro)
        visualizacao = rm.formatar_padroes_para_exibicao(padroes)

        return sucesso(
            "Padrões arquiteturais do projeto",
            {
                "padroes": padroes,
                "visualizacao": visualizacao,
                "total": len(padroes)
            }
        )

    except Exception as e:
        return falha(str(e), "ERRO_CONSULTAR_PADROES")


def consultar_memoria_arquitetural() -> dict:
    """
    Consulta toda a memória arquitetural do projeto.
    """
    try:
        rm = _obter_rule_manager()
        tudo = rm.consultar_tudo()

        # Formata para exibição
        linhas = []
        linhas.append("=" * 60)
        linhas.append("🏗️ MEMÓRIA ARQUITETURAL DO PROJETO")
        linhas.append("=" * 60)
        linhas.append("")

        # Informações do projeto
        projeto = tudo.get("projeto", {})
        if projeto.get("nome") or projeto.get("linguagem"):
            linhas.append("📋 INFORMAÇÕES DO PROJETO:")
            if projeto.get("nome"):
                linhas.append(f"  Nome: {projeto['nome']}")
            if projeto.get("linguagem"):
                linhas.append(f"  Linguagem: {projeto['linguagem']}")
                if projeto.get("versao_linguagem"):
                    linhas.append(f"  Versão: {projeto['versao_linguagem']}")
            if projeto.get("framework"):
                linhas.append(f"  Framework: {projeto['framework']}")
            linhas.append("")

        # Regras
        regras = tudo.get("regras", [])
        if regras:
            linhas.append(f"📋 REGRAS ({len(regras)}):")
            for regra in regras[:10]:  # Limita a 10
                obrigatoria = "🔴" if regra.get("obrigatoria", True) else "🟡"
                linhas.append(f"  {obrigatoria} {regra['regra']}")
            linhas.append("")

        # Padrões
        padroes = tudo.get("padroes_arquiteturais", [])
        if padroes:
            linhas.append(f"🏗️ PADRÕES ({len(padroes)}):")
            for padrao in padroes[:10]:  # Limita a 10
                linhas.append(f"  • {padrao['nome']}: {padrao['descricao']}")
            linhas.append("")

        # Decisões
        decisoes = tudo.get("decisoes_tecnicas", [])
        if decisoes:
            linhas.append(f"💡 DECISÕES TÉCNICAS ({len(decisoes)}):")
            for decisao in decisoes[-5:]:  # Últimas 5
                linhas.append(f"  • {decisao['decisao']}")
            linhas.append("")

        # Restrições
        restricoes = tudo.get("restricoes", [])
        if restricoes:
            linhas.append(f"🚫 RESTRIÇÕES ({len(restricoes)}):")
            for restricao in restricoes[:10]:  # Limita a 10
                linhas.append(f"  • {restricao['restricao']}")
            linhas.append("")

        linhas.append("=" * 60)

        visualizacao = "\n".join(linhas)

        return sucesso(
            "Memória arquitetural do projeto",
            {
                "memoria": tudo,
                "visualizacao": visualizacao
            }
        )

    except Exception as e:
        return falha(str(e), "ERRO_CONSULTAR_MEMORIA")
