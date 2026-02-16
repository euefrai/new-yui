"""
Analisador arquitetural: identifica responsabilidades e padrões a partir da estrutura.
SOMENTE LEITURA.
"""

from typing import Dict, List

# Mapeamento genérico: nome de pasta → descrição de responsabilidade
RESPONSIBILITY_MAP = {
    "core": "Lógica central: parser, decisão, execução",
    "actions": "Ações do sistema e orquestração",
    "gui": "Interface gráfica",
    "validation": "Validação: sintaxe, testes, linter",
    "architecture": "Memória arquitetural e regras",
    "code_editor": "Edição de código: diff, patch, planejamento",
    "memory": "Memória de conversa e perfil",
    "config": "Configuração",
    "permissions": "Permissões",
    "voice": "Voz e reconhecimento",
    "analyzer": "Análise de projetos (scanner, dependências, relatórios)",
    "system": "Sistema: indexação, launcher",
}


def analyze_architecture(scanner_data: Dict) -> Dict:
    """
    Identifica responsabilidades e padrões a partir da estrutura do projeto.

    Returns:
        Dict com: responsabilidades, camadas, padroes.
    """
    modulos = scanner_data.get("modulos_principais", [])
    responsabilidades = {
        m: RESPONSIBILITY_MAP.get(m, "Módulo do projeto")
        for m in modulos
    }

    camadas: List[str] = []
    if "core" in modulos:
        camadas.append("core — núcleo (parser, execução)")
    if "actions" in modulos:
        camadas.append("actions — orquestração de ações")
    if "gui" in modulos:
        camadas.append("gui — interface de usuário")
    if "validation" in modulos or "code_editor" in modulos:
        camadas.append("code_editor/validation — edição e validação")
    if "architecture" in modulos:
        camadas.append("architecture — memória e regras")
    if "analyzer" in modulos:
        camadas.append("analyzer — análise técnica (somente leitura)")

    padroes: List[str] = []
    if len(modulos) > 3:
        padroes.append("Separação por responsabilidade (pastas por domínio)")
    if "code_editor" in modulos and "validation" in modulos:
        padroes.append("Edição e validação em módulos distintos")
    if "core" in modulos:
        padroes.append("Núcleo isolado em core/")
    if "analyzer" in modulos:
        padroes.append("Análise isolada em analyzer/")

    return {
        "responsabilidades": responsabilidades,
        "camadas": camadas,
        "padroes": padroes,
    }
