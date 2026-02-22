"""
Classificador leve de intenção — direciona para Yui ou Heathcliff.
Heathcliff: perguntas técnicas (código, arquitetura, segurança, etc).
Yui: perguntas gerais, casuais, curiosidades.
"""

# Palavras que indicam intenção técnica → Heathcliff
TECH_KEYWORDS = frozenset([
    "código", "codigo", "code", "bug", "erro", "error", "exception",
    "python", "javascript", "typescript", "java", "rust", "go", "php",
    "api", "rest", "graphql", "banco", "database", "sql", "query",
    "arquitetura", "architecture", "estrutura", "pastas", "projeto",
    "performance", "otimizar", "optimize", "vulnerabilidade", "security",
    "segurança", "teste", "test", "deploy", "docker", "kubernetes",
    "função", "funcao", "function", "classe", "class", "método", "metodo",
    "import", "require", "npm", "pip", "package", "dependência",
    "async", "await", "promise", "callback", "hook", "react", "vue",
    "backend", "frontend", "fullstack", "microserviço", "microservice",
])


def classificar_intencao(mensagem: str) -> str:
    """
    Retorna "heathcliff" se a mensagem for técnica, "yui" caso contrário.
    """
    if not mensagem or not isinstance(mensagem, str):
        return "yui"

    t = mensagem.lower().strip()

    # Blocos de código (```) → técnico
    if "```" in t:
        return "heathcliff"

    # Verificar palavras-chave (exact match O(1), substring com any() short-circuit)
    words = set(t.split())
    for w in words:
        if len(w) < 3:
            continue
        if w in TECH_KEYWORDS:
            return "heathcliff"
        if any(kw in w or w in kw for kw in TECH_KEYWORDS):
            return "heathcliff"

    return "yui"
