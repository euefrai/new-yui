"""
Compacta o projeto Yui no menor tamanho possível para enviar (ex.: para um amigo analisar).
Gera um ZIP só com código fonte, requirements e docs; exclui .git, venv, dados e caches.

Uso: python compactar_para_envio.py
Saída: yui-envio.zip (na pasta do projeto)
"""
import zipfile
from pathlib import Path

# Raiz do projeto (pasta onde está este script)
BASE = Path(__file__).resolve().parent

# Pastas/arquivos que deixam o projeto pesado — NÃO incluir no ZIP
EXCLUIR_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "generated_projects",
    "chroma",
    "yui_vector_db",
    "data",
    "scripts",  # scripts de zip gerados pela própria Yui
    ".pytest_cache",
    "node_modules",
    ".idea",
    ".vscode",
    ".cursor",
    "dist",
    "build",
    "*.egg-info",
    ".eggs",
}
EXCLUIR_EXT = {".pyc", ".pyo", ".pyd", ".so", ".zip", ".exe", ".log"}
EXCLUIR_ARQUIVOS = {".env", ".DS_Store", "Thumbs.db"}  # .env tem secrets


def deve_excluir(path: Path, rel: Path) -> bool:
    """True se o arquivo/pasta não deve entrar no ZIP."""
    nome = path.name
    if nome in EXCLUIR_ARQUIVOS:
        return True
    if path.suffix.lower() in EXCLUIR_EXT:
        return True
    for part in rel.parts:
        if part in EXCLUIR_DIRS:
            return True
        if part.endswith(".egg-info"):
            return True
    return False


def main():
    zip_path = BASE / "yui-envio.zip"
    # Remove ZIP antigo se existir
    if zip_path.exists():
        zip_path.unlink()

    count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(BASE.rglob("*")):
            if not path.is_file():
                continue
            try:
                rel = path.relative_to(BASE)
            except ValueError:
                continue
            if deve_excluir(path, rel):
                continue
            # Nome no ZIP: sem drive, sempre com /
            arcname = rel.as_posix()
            zf.write(path, arcname)
            count += 1

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"OK: {count} arquivos em {zip_path.name} ({size_mb:.2f} MB)")
    print("Envie esse arquivo. Quem receber: descompacte e rode pip install -r requirements.txt")


if __name__ == "__main__":
    main()
