# ==========================================================
# YUI VECTOR MEMORY
# Memória vetorial do projeto: embeddings + busca semântica.
# ==========================================================

import os
from pathlib import Path
from typing import List

try:
    from config.settings import BASE_DIR
except Exception:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
PASTA_DB = str(BASE_DIR / "yui_vector_db")
EXTENSOES = (".py", ".js", ".ts", ".html", ".css", ".json", ".md", ".yaml", ".yml")
IGNORAR = {"__pycache__", ".git", "node_modules", "venv", ".venv", "env", "dist", "build"}

_client = None
_collection = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    try:
        import chromadb
        from chromadb.config import Settings
        _client = chromadb.PersistentClient(path=PASTA_DB, settings=Settings(anonymized_telemetry=False))
        return _client
    except Exception:
        return None


def _get_embedding_function():
    try:
        from chromadb.utils import embedding_functions
        api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
        if api_key:
            return embedding_functions.OpenAIEmbeddingFunction(api_key=api_key, model_name="text-embedding-3-small")
        return embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    except Exception:
        return None


def _get_collection():
    global _collection
    if _collection is not None:
        return _collection
    client = _get_client()
    if not client:
        return None
    try:
        ef = _get_embedding_function()
        if not ef:
            return None
        _collection = client.get_or_create_collection(
            name="projeto_yui",
            embedding_function=ef,
            metadata={"description": "Trechos do projeto YUI"}
        )
        return _collection
    except Exception:
        return None


# ==========================================================
# QUEBRAR TEXTO EM PARTES
# ==========================================================

def chunk_text(texto: str, tamanho: int = 800) -> List[str]:
    if not texto:
        return []
    return [texto[i : i + tamanho] for i in range(0, len(texto), tamanho)]


# ==========================================================
# INDEXAR PROJETO
# ==========================================================

def indexar_projeto(raiz: str) -> int:
    """Percorre a árvore do projeto, quebra arquivos em chunks e indexa no ChromaDB. Retorna quantidade de blocos indexados."""
    raiz = os.path.abspath(raiz)
    if not os.path.isdir(raiz):
        return 0

    coll = _get_collection()
    if not coll:
        return 0

    ids: List[str] = []
    docs: List[str] = []

    for root, dirs, files in os.walk(raiz):
        dirs[:] = [d for d in dirs if d not in IGNORAR]
        for f in files:
            if not any(f.endswith(ext) for ext in EXTENSOES):
                continue
            caminho = os.path.join(root, f)
            try:
                with open(caminho, "r", encoding="utf-8", errors="ignore") as arq:
                    conteudo = arq.read()
            except Exception:
                continue
            partes = chunk_text(conteudo)
            for i, parte in enumerate(partes):
                ids.append(f"{caminho}_{i}")
                docs.append(parte)

    if docs:
        coll.upsert(ids=ids, documents=docs)
        _get_client().persist()
    return len(docs)


# ==========================================================
# BUSCAR CONTEXTO RELEVANTE
# ==========================================================

def buscar_contexto(query: str, limite: int = 5) -> str:
    """Busca na memória vetorial os trechos mais relevantes para a pergunta. Retorna texto formatado ou string vazia."""
    if not (query or query.strip()):
        return ""
    coll = _get_collection()
    if not coll:
        return ""
    try:
        resultados = coll.query(query_texts=[query.strip()], n_results=limite)
        if not resultados or not resultados.get("documents") or not resultados["documents"][0]:
            return ""
        blocos = resultados["documents"][0]
        contexto = "\n\n".join(blocos)
        return f"\n### MEMÓRIA DO PROJETO (trechos relevantes)\n{contexto}\n"
    except Exception:
        return ""
