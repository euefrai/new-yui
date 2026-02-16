"""
Analisador de qualidade: detecta riscos e pontos fracos/fortes.
SOMENTE LEITURA — não executa código.
"""

from typing import Dict, List


def analisar_qualidade(dados_scanner: Dict, dados_arquitetura: Dict) -> Dict:
    """Avalia pontos fortes, fracos e riscos técnicos (estruturais)."""
    modulos = dados_scanner.get("modulos_principais", [])
    total = dados_scanner.get("total_arquivos", 0)
    extensoes = dados_scanner.get("extensoes", {})

    pontos_fortes = []
    if "core" in modulos and "actions" in modulos:
        pontos_fortes.append("Separação clara entre núcleo (core) e ações (actions)")
    if "code_editor" in modulos:
        pontos_fortes.append("Módulo dedicado de edição de código (diff/patch)")
    if "validation" in modulos:
        pontos_fortes.append("Validação pós-edição (sintaxe, testes, linter)")
    if "architecture" in modulos:
        pontos_fortes.append("Memória arquitetural para regras e padrões")
    if "gui" in modulos:
        pontos_fortes.append("Interface gráfica separada do fluxo principal")
    if extensoes.get(".py", 0) > 10:
        pontos_fortes.append("Projeto modular com múltiplos módulos Python")

    pontos_fracos = []
    if total > 100 and len(modulos) < 5:
        pontos_fracos.append("Muitos arquivos em poucas pastas — considerar subdivisão")
    if "core" not in modulos and total > 20:
        pontos_fracos.append("Núcleo não em core/ — pode dificultar manutenção")
    if not pontos_fracos:
        pontos_fracos.append("Nenhum ponto fraco estrutural evidente.")

    riscos = []
    if total > 200:
        riscos.append("Projeto grande: manter documentação e testes atualizados")
    if len(modulos) > 15:
        riscos.append("Muitos módulos: atenção a dependências circulares")
    if not riscos:
        riscos.append("Nenhum risco técnico estrutural evidente.")

    return {"pontos_fortes": pontos_fortes, "pontos_fracos": pontos_fracos, "riscos_tecnicos": riscos}
