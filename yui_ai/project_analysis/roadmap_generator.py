"""
Gerador de roadmap técnico a partir da análise.
SOMENTE LEITURA — sugestões baseadas em estrutura.
"""

from typing import Dict, List


def gerar_roadmap(dados_scanner: Dict, dados_arquitetura: Dict, dados_qualidade: Dict) -> Dict:
    """Gera roadmap curto, médio e longo prazo."""
    modulos = dados_scanner.get("modulos_principais", [])
    pontos_fracos = dados_qualidade.get("pontos_fracos", [])
    riscos = dados_qualidade.get("riscos_tecnicos", [])

    curto = [
        "Manter documentação (README, ANALISE_PROJETO.md) atualizada",
        "Garantir cobertura de testes nos módulos críticos (validation, code_editor)" if "validation" in modulos else "Revisar testes nos módulos críticos",
        "Revisar dependências opcionais (voz, automação) para evitar falhas de import",
    ]
    medio = [
        "Endereçar pontos fracos estruturais identificados na análise" if pontos_fracos else "Manter estrutura atual",
        "Considerar testes de integração para o fluxo completo (parser → ação → validação)",
        "Documentar contrato entre GUI e core (YuiBridge)" if "gui" in modulos else "Documentar fluxo principal",
    ]
    longo = [
        "Avaliar modularização adicional se o projeto crescer",
        "Monitorar dependências circulares e acoplamento" if riscos else "Manter acoplamento sob controle",
        "Alinhar roadmap com decisões da memória arquitetural",
    ]
    return {"curto_prazo": curto, "medio_prazo": medio, "longo_prazo": longo}
