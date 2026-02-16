"""
Engine de validação completa pós-edição.

Executa todas as validações após aplicar código e relata resultados.
"""

from typing import Dict, List, Optional, Tuple
from yui_ai.validation.syntax_validator import validar_sintaxe
from yui_ai.validation.test_runner import executar_testes
from yui_ai.validation.linter_runner import executar_linter


class ValidationEngine:
    """
    Gerencia validação completa após edição de código.
    """

    def __init__(self):
        self.resultados_validacao: List[Dict] = []

    def validar_apos_edicao(
        self,
        arquivo_modificado: str,
        diretorio_projeto: Optional[str] = None
    ) -> Dict:
        """
        Executa validação completa após edição.

        Retorna: {
            "sucesso_geral": bool,
            "sintaxe": {...},
            "testes": {...},
            "linter": {...},
            "resumo": str,
            "tem_erros": bool
        }
        """
        resultados = {
            "arquivo": arquivo_modificado,
            "sintaxe": {},
            "testes": {},
            "linter": {},
            "tem_erros": False,
            "resumo": ""
        }

        # 1. Validação de sintaxe
        sintaxe_ok, sintaxe_saida, sintaxe_erro = validar_sintaxe(arquivo_modificado)
        resultados["sintaxe"] = {
            "sucesso": sintaxe_ok,
            "saida": sintaxe_saida,
            "erro": sintaxe_erro
        }

        if not sintaxe_ok:
            resultados["tem_erros"] = True

        # 2. Execução de testes (se existirem)
        testes_ok, testes_saida, testes_erro, testes_detalhes = executar_testes(
            arquivo_modificado,
            diretorio_projeto
        )
        resultados["testes"] = {
            "sucesso": testes_ok,
            "saida": testes_saida,
            "erro": testes_erro,
            "detalhes": testes_detalhes
        }

        if not testes_ok and testes_detalhes.get("testes_executados", 0) > 0:
            resultados["tem_erros"] = True

        # 3. Execução de linter (se existir)
        linter_ok, linter_saida, linter_erro, linter_detalhes = executar_linter(
            arquivo_modificado,
            diretorio_projeto
        )
        resultados["linter"] = {
            "sucesso": linter_ok,
            "saida": linter_saida,
            "erro": linter_erro,
            "detalhes": linter_detalhes
        }

        if not linter_ok:
            resultados["tem_erros"] = True

        # 4. Gera resumo
        resultados["resumo"] = self._gerar_resumo(resultados)
        resultados["sucesso_geral"] = not resultados["tem_erros"]

        # 5. Salva resultado
        self.resultados_validacao.append(resultados)

        return resultados

    def _gerar_resumo(self, resultados: Dict) -> str:
        """Gera resumo legível dos resultados."""
        linhas = []

        # Sintaxe
        sintaxe = resultados["sintaxe"]
        if sintaxe["sucesso"]:
            linhas.append("✅ Sintaxe: válida")
        else:
            linhas.append("❌ Sintaxe: ERRO")
            if sintaxe["erro"]:
                linhas.append(f"   {sintaxe['erro'][:100]}...")

        # Testes
        testes = resultados["testes"]
        detalhes_teste = testes.get("detalhes", {})
        if detalhes_teste.get("testes_executados", 0) > 0:
            if testes["sucesso"]:
                linhas.append(f"✅ Testes: {detalhes_teste['testes_passaram']}/{detalhes_teste['testes_executados']} passaram")
            else:
                linhas.append(f"❌ Testes: {detalhes_teste['testes_falharam']} falharam")
        else:
            linhas.append("ℹ️  Testes: nenhum framework detectado")

        # Linter
        linter = resultados["linter"]
        detalhes_linter = linter.get("detalhes", {})
        if detalhes_linter.get("linter") != "nenhum":
            if linter["sucesso"]:
                linhas.append(f"✅ Linter ({detalhes_linter['linter']}): sem erros")
            else:
                linhas.append(f"❌ Linter ({detalhes_linter['linter']}): {detalhes_linter.get('erros', 0)} erros")
        else:
            linhas.append("ℹ️  Linter: nenhum detectado")

        return "\n".join(linhas)

    def formatar_resultado_completo(self, resultado: Dict) -> str:
        """Formata resultado completo para exibição."""
        linhas = []
        linhas.append("=" * 60)
        linhas.append("📋 RESULTADO DA VALIDAÇÃO")
        linhas.append("=" * 60)
        linhas.append("")
        linhas.append(resultado["resumo"])
        linhas.append("")

        # Detalhes de sintaxe se houver erro
        if not resultado["sintaxe"]["sucesso"]:
            linhas.append("🔴 ERRO DE SINTAXE:")
            linhas.append("-" * 60)
            if resultado["sintaxe"]["erro"]:
                linhas.append(resultado["sintaxe"]["erro"])
            linhas.append("")

        # Detalhes de testes se houver falhas
        if not resultado["testes"]["sucesso"] and resultado["testes"].get("detalhes", {}).get("testes_executados", 0) > 0:
            linhas.append("🔴 FALHAS NOS TESTES:")
            linhas.append("-" * 60)
            if resultado["testes"]["erro"]:
                # Mostra últimas 20 linhas do erro
                erro_linhas = resultado["testes"]["erro"].split("\n")
                linhas.extend(erro_linhas[-20:])
            linhas.append("")

        # Detalhes de linter se houver erros
        if not resultado["linter"]["sucesso"]:
            linhas.append("🔴 ERROS DO LINTER:")
            linhas.append("-" * 60)
            if resultado["linter"]["erro"]:
                # Mostra últimas 20 linhas do erro
                erro_linhas = resultado["linter"]["erro"].split("\n")
                linhas.extend(erro_linhas[-20:])
            linhas.append("")

        linhas.append("=" * 60)

        return "\n".join(linhas)
