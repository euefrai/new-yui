"""
Analisador arquitetural: identifica responsabilidades e padrões.
SOMENTE LEITURA — baseado em estrutura e nomes.
"""

from typing import Dict, List

MAPEAMENTO = {
    "core": "Lógica central: parser, IA, decisão, execução, file resolver",
    "actions": "Ações do sistema: dispatcher, código, arquitetura",
    "gui": "Interface gráfica: janela, chat, bridge",
    "validation": "Validação pós-edição: sintaxe, testes, linter",
    "architecture": "Memória arquitetural: regras, padrões",
    "code_editor": "Edição de código: diff, patch, planejamento, IA",
    "memory": "Memória de conversa e perfil",
    "config": "Configuração e persona",
    "permissions": "Permissões",
    "voice": "Voz e reconhecimento",
}


def analisar_arquitetura(dados_scanner: Dict) -> Dict:
    """Identifica responsabilidades e padrões a partir da estrutura."""
    modulos = dados_scanner.get("modulos_principais", [])
    responsabilidades = {m: MAPEAMENTO.get(m, "Módulo do projeto") for m in modulos}
    if "yui_ai" in modulos:
        responsabilidades["yui_ai"] = "Pacote principal do assistente"

    camadas = []
    if "core" in modulos:
        camadas.append("core — núcleo (parser, IA, execução)")
    if "actions" in modulos:
        camadas.append("actions — orquestração de ações")
    if "gui" in modulos:
        camadas.append("gui — interface de usuário")
    if "validation" in modulos or "code_editor" in modulos:
        camadas.append("code_editor/validation — edição e validação")
    if "architecture" in modulos:
        camadas.append("architecture — memória e regras")

    padroes = []
    if len(modulos) > 3:
        padroes.append("Separação por responsabilidade (pastas por domínio)")
    if "code_editor" in modulos and "validation" in modulos:
        padroes.append("Edição e validação em módulos distintos")
    if "core" in modulos:
        padroes.append("Núcleo isolado em core/")

    return {"responsabilidades": responsabilidades, "camadas": camadas, "padroes": padroes}
