"""
Detector de riscos: problemas arquiteturais, acoplamento, ciclos, qualidade.
SOMENTE LEITURA.
"""

from typing import Dict, List


def detect_risks(
    scanner_data: Dict,
    architecture_data: Dict,
    dependency_data: Dict,
) -> Dict:
    """
    Agrega pontos fortes, fracos e riscos técnicos (estrutura + dependências).

    Returns:
        Dict com: pontos_fortes, pontos_fracos, riscos_tecnicos, ciclos.
    """
    modulos = scanner_data.get("modulos_principais", [])
    total = scanner_data.get("total_arquivos", 0)
    extensoes = scanner_data.get("extensoes", {})
    n_py = extensoes.get(".py", 0)

    dep_stats = dependency_data.get("stats", {})
    ciclos = dependency_data.get("circular", [])
    n_ciclos = dep_stats.get("ciclos", 0)

    pontos_fortes: List[str] = []
    if "core" in modulos and "actions" in modulos:
        pontos_fortes.append("Separação clara entre núcleo (core) e ações (actions)")
    if "code_editor" in modulos:
        pontos_fortes.append("Módulo dedicado de edição de código (diff/patch)")
    if "validation" in modulos:
        pontos_fortes.append("Validação pós-edição (sintaxe, testes, linter)")
    if "architecture" in modulos:
        pontos_fortes.append("Memória arquitetural para regras e padrões")
    if "analyzer" in modulos:
        pontos_fortes.append("Módulo de análise técnica isolado (analyzer)")
    if n_py > 10:
        pontos_fortes.append("Projeto modular com múltiplos módulos Python")
    if not pontos_fortes:
        pontos_fortes.append("Estrutura básica identificada.")

    pontos_fracos: List[str] = []
    if total > 100 and len(modulos) < 5:
        pontos_fracos.append("Muitos arquivos em poucas pastas — considerar subdivisão")
    if "core" not in modulos and total > 20:
        pontos_fracos.append("Núcleo não em core/ — pode dificultar manutenção")
    if n_ciclos > 0:
        pontos_fracos.append(f"Dependências circulares detectadas: {n_ciclos} ciclo(s)")
    if not pontos_fracos:
        pontos_fracos.append("Nenhum ponto fraco estrutural evidente.")

    riscos_tecnicos: List[str] = []
    if total > 200:
        riscos_tecnicos.append("Projeto grande: manter documentação e testes atualizados")
    if len(modulos) > 15:
        riscos_tecnicos.append("Muitos módulos: atenção a dependências circulares")
    if n_ciclos > 0:
        riscos_tecnicos.append("Ciclos de import podem causar falhas em tempo de carga")
    if not riscos_tecnicos:
        riscos_tecnicos.append("Nenhum risco técnico estrutural evidente.")

    return {
        "pontos_fortes": pontos_fortes,
        "pontos_fracos": pontos_fracos,
        "riscos_tecnicos": riscos_tecnicos,
        "ciclos": ciclos,
    }
