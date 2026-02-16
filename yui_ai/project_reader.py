import os
import ast

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def ler_arquivo_py(nome_arquivo):
    caminho = os.path.join(BASE_DIR, nome_arquivo)

    if not os.path.exists(caminho):
        return None, "Arquivo não encontrado."

    if not nome_arquivo.endswith(".py"):
        return None, "Apenas arquivos .py são permitidos."

    with open(caminho, "r", encoding="utf-8") as f:
        codigo = f.read()

    return codigo, None


def extrair_info_codigo(codigo):
    arvore = ast.parse(codigo)

    funcoes = []
    classes = []
    imports = []

    for node in ast.walk(arvore):
        if isinstance(node, ast.FunctionDef):
            funcoes.append(node.name)

        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)

        elif isinstance(node, ast.Import):
            for n in node.names:
                imports.append(n.name)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    return {
        "funcoes": funcoes,
        "classes": classes,
        "imports": imports
    }


def listar_arquivos_py(pasta="."):
    arquivos = []
    for root, _, files in os.walk(pasta):
        for file in files:
            if file.endswith(".py") and "__pycache__" not in root:
                arquivos.append(os.path.join(root, file))
    return arquivos


def ler_projeto_completo():
    arquivos = listar_arquivos_py()
    projeto = {}

    for arq in arquivos:
        try:
            with open(arq, "r", encoding="utf-8") as f:
                codigo = f.read()

            info = extrair_info_codigo(codigo)
            tipo, responsabilidade = classificar_arquivo(arq, info)

            projeto[arq] = {
                "tipo": tipo,
                "responsabilidade": responsabilidade,
                "funcoes": info["funcoes"],
                "classes": info["classes"]
            }

        except Exception as e:
            continue

    return projeto   # 🔥 ESSENCIAL



def classificar_arquivo(nome_arquivo, info):
    nome = nome_arquivo.lower()

    if "main" in nome:
        return "core", "orquestração principal"

    if any(k in nome for k in ["engine", "ai", "brain"]):
        return "core", "inteligência e tomada de decisão"

    if any(k in nome for k in ["memory", "storage"]):
        return "infra", "gerenciamento de estado e memória"

    if any(k in nome for k in ["voice", "audio", "ui", "panel"]):
        return "interface", "interação com o usuário"

    if any(k in nome for k in ["action", "permission"]):
        return "infra", "execução e controle de ações"

    return "util", "funções auxiliares"


def calcular_acoplamento(projeto):
    relatorio = []

    for arquivo, info in projeto.items():
        total_imports = len(info.get("imports", []))

        nivel = "baixo"
        if total_imports >= 5:
            nivel = "medio"
        if total_imports >= 8:
            nivel = "alto"

        relatorio.append({
            "arquivo": arquivo,
            "imports": info.get("imports", []),
            "total": total_imports,
            "nivel": nivel,
            "tipo": info.get("tipo"),
            "responsabilidade": info.get("responsabilidade")
        })

    return relatorio
