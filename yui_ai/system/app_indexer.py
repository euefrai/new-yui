"""
Sistema profissional de indexação de aplicativos (somente leitura).

- Nunca executa arquivos durante a indexação.
- Nunca escaneia pastas pessoais (Documentos, Downloads, Fotos).
- Nunca envia dados para a nuvem.
- Índice salvo localmente em %LOCALAPPDATA%/Yui/app_index.json.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

# Caminhos permitidos para indexação (somente estes)
_PROGRAM_FILES = os.environ.get("ProgramFiles", "C:\\Program Files")
_PROGRAM_FILES_X86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
_LOCAL_APPDATA = os.environ.get("LOCALAPPDATA", "")
_ROAMING_APPDATA = os.environ.get("APPDATA", "")
_USERPROFILE = os.environ.get("USERPROFILE", "")
_PROGRAM_DATA = os.environ.get("PROGRAMDATA", "")
_PUBLIC = os.environ.get("PUBLIC", os.path.expandvars("%PUBLIC%"))

# Pastas permitidas (raiz; a indexação percorre subpastas com limites)
_PASTAS_PERMITIDAS: List[tuple] = []
if _PROGRAM_FILES and os.path.isdir(_PROGRAM_FILES):
    _PASTAS_PERMITIDAS.append((_PROGRAM_FILES, "Program Files", 3))
if _PROGRAM_FILES_X86 and os.path.isdir(_PROGRAM_FILES_X86):
    _PASTAS_PERMITIDAS.append((_PROGRAM_FILES_X86, "Program Files (x86)", 3))
if _LOCAL_APPDATA:
    programs_local = os.path.join(_LOCAL_APPDATA, "Programs")
    if os.path.isdir(programs_local):
        _PASTAS_PERMITIDAS.append((programs_local, "AppData\\Local\\Programs", 3))
if _ROAMING_APPDATA and os.path.isdir(_ROAMING_APPDATA):
    _PASTAS_PERMITIDAS.append((_ROAMING_APPDATA, "AppData", 2))
# Menu Iniciar (usuário e global)
if _ROAMING_APPDATA:
    start_user = os.path.join(_ROAMING_APPDATA, "Microsoft", "Windows", "Start Menu")
    if os.path.isdir(start_user):
        _PASTAS_PERMITIDAS.append((start_user, "Start Menu", 2))
if _PROGRAM_DATA:
    start_global = os.path.join(_PROGRAM_DATA, "Microsoft", "Windows", "Start Menu")
    if os.path.isdir(start_global):
        _PASTAS_PERMITIDAS.append((start_global, "Start Menu", 2))
elif _PUBLIC:
    start_global = os.path.join(_PUBLIC, "Microsoft", "Windows", "Start Menu")
    if os.path.isdir(start_global):
        _PASTAS_PERMITIDAS.append((start_global, "Start Menu", 2))
# Desktop (apenas .lnk)
if _USERPROFILE:
    desktop_user = os.path.join(_USERPROFILE, "Desktop")
    if os.path.isdir(desktop_user):
        _PASTAS_PERMITIDAS.append((desktop_user, "Desktop", 0))
if _PUBLIC:
    desktop_public = os.path.join(_PUBLIC, "Desktop")
    if os.path.isdir(desktop_public):
        _PASTAS_PERMITIDAS.append((desktop_public, "Desktop", 0))

# Nomes de pastas/arquivos a ignorar
_IGNORAR_DIRS = {"__pycache__", ".git", "node_modules", "tmp", "temp", "cache", ".cache"}
_IGNORAR_EXT_TEMP = {".tmp", ".temp", ".bak", ".log"}


def get_index_path() -> str:
    """Retorna o caminho do arquivo de índice (não cria pasta)."""
    base = _LOCAL_APPDATA or os.path.expanduser("~")
    dir_yui = os.path.join(base, "Yui")
    return os.path.join(dir_yui, "app_index.json")


def _normalizar_nome_canonico(nome: str) -> str:
    """Remove .exe/.lnk, lowercase, remove símbolos comuns."""
    if not nome:
        return ""
    s = nome.strip().lower()
    for ext in (".exe", ".lnk", ".com", ".bat", ".cmd"):
        if s.endswith(ext):
            s = s[: -len(ext)]
            break
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _ler_alvo_lnk(caminho_lnk: str) -> Optional[str]:
    """Lê o alvo de um atalho .lnk (somente leitura, não executa)."""
    if not caminho_lnk.lower().endswith(".lnk") or not os.path.isfile(caminho_lnk):
        return None
    try:
        import struct
        with open(caminho_lnk, "rb") as f:
            content = f.read()
        if len(content) < 0x4C or content[:4] != b"L\x00\x00\x00":
            return None
        ofs = 0x4C
        flags = struct.unpack("<I", content[0x14:0x18])[0]
        if flags & 1:
            ofs += 0x60
        pos = content.find(b"\x00\x00\x00", ofs)
        if pos == -1:
            return None
        s = content[ofs:pos].decode("utf-16-le", errors="ignore").strip()
        return s if s else None
    except Exception:
        return None


def _gerar_aliases(arquivo: str, pasta_pai: str, tipo: str, nome_lnk: Optional[str] = None) -> List[str]:
    """Gera aliases: nome da pasta, nome do executável, nome humano (lnk)."""
    aliases: Set[str] = set()
    base_name = os.path.splitext(os.path.basename(arquivo))[0]
    canon = _normalizar_nome_canonico(base_name)
    if canon:
        aliases.add(canon)
    # Nome da pasta (ex.: "Google Chrome" -> chrome)
    if pasta_pai:
        pai_canon = _normalizar_nome_canonico(pasta_pai)
        if pai_canon and pai_canon != canon:
            aliases.add(pai_canon)
    # Nome do atalho (sem .lnk)
    if nome_lnk:
        lnk_canon = _normalizar_nome_canonico(nome_lnk)
        if lnk_canon:
            aliases.add(lnk_canon)
    # Nome “humano” comum: "visual studio code" -> "code", "vscode"
    if "visual studio code" in canon or "code" == base_name.lower():
        aliases.add("vscode")
        aliases.add("code")
    if "google chrome" in canon or "chrome" in base_name.lower():
        aliases.add("chrome")
        aliases.add("google chrome")
    # Telegram: "telegram desktop" -> telegram, telegramdesktop
    if "telegram" in canon or (nome_lnk and "telegram" in nome_lnk.lower()) or (pasta_pai and "telegram" in pasta_pai.lower()):
        aliases.add("telegram")
        aliases.add("telegram desktop")
        aliases.add("telegramdesktop")
    # Variante sem espaços para qualquer nome com mais de uma palavra
    for a in list(aliases):
        if " " in a:
            aliases.add(a.replace(" ", ""))
    return list(aliases)


def _deve_ignorar_dir(nome_dir: str) -> bool:
    if not nome_dir:
        return True
    n = nome_dir.lower()
    if n in _IGNORAR_DIRS:
        return True
    if n.startswith("."):
        return True
    return False


def _coletar_exe_em_pasta(raiz: str, profundidade_max: int, source: str) -> List[Dict[str, Any]]:
    """Percorre pasta coletando .exe (somente leitura)."""
    entradas: List[Dict[str, Any]] = []
    try:
        for root, dirs, files in os.walk(raiz, topdown=True):
            rel = os.path.relpath(root, raiz)
            if rel == ".":
                nivel = 0
            else:
                nivel = rel.count(os.sep) + 1
            if nivel > profundidade_max:
                dirs.clear()
                continue
            dirs[:] = [d for d in dirs if not _deve_ignorar_dir(d)]
            for f in files:
                if not f.lower().endswith(".exe"):
                    continue
                path_full = os.path.join(root, f)
                if not os.path.isfile(path_full):
                    continue
                nome_base = os.path.splitext(f)[0]
                pasta_pai = os.path.basename(root)
                canon = _normalizar_nome_canonico(nome_base)
                if not canon:
                    continue
                aliases = _gerar_aliases(path_full, pasta_pai, "exe", None)
                size_bytes = 0
                try:
                    if os.path.isfile(path_full):
                        size_bytes = os.path.getsize(path_full)
                except (OSError, PermissionError):
                    pass
                entradas.append({
                    "nome_canonico": canon,
                    "aliases": list(dict.fromkeys(aliases)),
                    "path": path_full,
                    "type": "exe",
                    "source": source,
                    "size_bytes": size_bytes,
                    "ultima_atualizacao": datetime.utcnow().isoformat() + "Z",
                })
    except (PermissionError, OSError):
        pass
    return entradas


def _coletar_lnk_em_pasta(pasta: str, source: str) -> List[Dict[str, Any]]:
    """Lista .lnk na pasta (um nível) e opcionalmente resolve alvo."""
    entradas: List[Dict[str, Any]] = []
    if not os.path.isdir(pasta):
        return entradas
    try:
        for f in os.listdir(pasta):
            if not f.lower().endswith(".lnk"):
                continue
            path_lnk = os.path.join(pasta, f)
            if not os.path.isfile(path_lnk):
                continue
            target = _ler_alvo_lnk(path_lnk)
            path_abrir = target if (target and os.path.exists(target)) else path_lnk
            nome_lnk = os.path.splitext(f)[0]
            canon = _normalizar_nome_canonico(nome_lnk)
            if not canon:
                canon = _normalizar_nome_canonico(os.path.basename(target)) if target else "atalho"
            aliases = _gerar_aliases(path_abrir, "", "lnk", nome_lnk)
            size_bytes = 0
            try:
                path_para_size = path_abrir if os.path.isfile(path_abrir) else path_lnk
                if os.path.isfile(path_para_size):
                    size_bytes = os.path.getsize(path_para_size)
            except (OSError, PermissionError):
                pass
            entradas.append({
                "nome_canonico": canon,
                "aliases": list(dict.fromkeys(aliases)),
                "path": path_abrir,
                "type": "lnk",
                "source": source,
                "size_bytes": size_bytes,
                "ultima_atualizacao": datetime.utcnow().isoformat() + "Z",
            })
    except (PermissionError, OSError):
        pass
    return entradas


def build_index(progress_callback: Optional[Callable[[str], None]] = None) -> tuple:
    """
    Constrói o índice em modo somente leitura.
    Retorna (sucesso: bool, total: int, mensagem: str).
    Nunca executa arquivos; nunca escaneia Documentos/Downloads/Fotos.
    """
    if sys.platform != "win32":
        return False, 0, "Indexação disponível apenas no Windows."

    todas: Dict[str, Dict[str, Any]] = {}
    total = 0

    def prog(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)

    for raiz, source, profundidade in _PASTAS_PERMITIDAS:
        prog(f"Indexando {source}...")
        if "Desktop" in source:
            itens = _coletar_lnk_em_pasta(raiz, source)
        elif "Start Menu" in source:
            itens = _coletar_lnk_em_pasta(raiz, source)
            try:
                for entry in os.listdir(raiz):
                    sub = os.path.join(raiz, entry)
                    if os.path.isdir(sub) and not _deve_ignorar_dir(entry):
                        itens.extend(_coletar_lnk_em_pasta(sub, source))
            except (PermissionError, OSError):
                pass
        else:
            itens = _coletar_exe_em_pasta(raiz, profundidade, source)

        for item in itens:
            canon = item["nome_canonico"]
            # Evita sobrescrever exe com lnk; prefere exe
            if canon in todas and todas[canon].get("type") == "exe" and item.get("type") == "lnk":
                continue
            # Mesmo canon: unir aliases
            if canon in todas:
                existing = todas[canon]
                all_aliases = set(existing.get("aliases", [])) | set(item.get("aliases", []))
                existing["aliases"] = list(all_aliases)
                continue
            todas[canon] = item
            total += 1

    dir_yui = os.path.dirname(get_index_path())
    try:
        os.makedirs(dir_yui, exist_ok=True)
    except OSError:
        return False, 0, "Não foi possível criar a pasta do índice."

    path_index = get_index_path()
    try:
        with open(path_index, "w", encoding="utf-8") as f:
            json.dump(todas, f, ensure_ascii=False, indent=2)
    except OSError as e:
        return False, 0, f"Erro ao salvar índice: {e}"

    return True, len(todas), "Índice salvo com sucesso."


def load_index() -> Dict[str, Dict[str, Any]]:
    """Carrega o índice do disco. Retorna dict vazio se não existir ou der erro."""
    path_index = get_index_path()
    if not os.path.isfile(path_index):
        return {}
    try:
        with open(path_index, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_index(indice: Dict[str, Dict[str, Any]]) -> bool:
    """Salva o índice no disco."""
    dir_yui = os.path.dirname(get_index_path())
    try:
        os.makedirs(dir_yui, exist_ok=True)
        with open(get_index_path(), "w", encoding="utf-8") as f:
            json.dump(indice, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


def search_index(nome: str) -> Optional[Dict[str, Any]]:
    """
    Busca um aplicativo no índice por nome canônico ou por qualquer alias.
    Retorna a entrada do índice ou None.
    """
    nome_norm = _normalizar_nome_canonico(nome)
    if not nome_norm:
        return None
    nome_sem_espacos = nome_norm.replace(" ", "")
    variantes = list(dict.fromkeys([nome_norm, nome_sem_espacos]))
    indice = load_index()
    # Busca exata por chave
    for q in variantes:
        if q in indice:
            return indice[q]
    # Busca por alias e match por prefixo (ex.: "telegram" encontra "telegram desktop")
    for canon, entry in indice.items():
        aliases = entry.get("aliases", [])
        for q in variantes:
            if q in aliases or q == canon:
                return entry
            if q in canon or (len(q) >= 4 and canon.startswith(q)):
                return entry
            for a in aliases:
                if q in a or a in q or (len(q) >= 4 and a.startswith(q)):
                    return entry
    return None


def _formatar_tamanho(size_bytes: int) -> str:
    """Formata tamanho em bytes para exibição (KB, MB, GB)."""
    if size_bytes <= 0:
        return "—"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def listar_indexados(limite: int = 200) -> List[Dict[str, Any]]:
    """Lista entradas do índice (nome_canonico, path, type, source)."""
    indice = load_index()
    out = []
    for canon, entry in indice.items():
        out.append({
            "nome_canonico": canon,
            "path": entry.get("path", ""),
            "type": entry.get("type", ""),
            "source": entry.get("source", ""),
        })
        if len(out) >= limite:
            break
    return out


def listar_indexados_com_filtros(
    filtro_nome: Optional[str] = None,
    ordenar_por: str = "nome",
    ordem_asc: bool = True,
    limite: int = 200,
) -> List[Dict[str, Any]]:
    """
    Lista entradas do índice com filtro e ordenação.
    - filtro_nome: substring para buscar em nome_canonico e aliases (case insensitive).
    - ordenar_por: 'nome' | 'tamanho' | 'origem' | 'tipo'
    - ordem_asc: True = A–Z / menor primeiro; False = Z–A / maior primeiro.
    - limite: número máximo de itens retornados.
    Retorna lista de dict com nome_canonico, path, type, source, size_bytes, tamanho_formatado.
    """
    indice = load_index()
    lista: List[Dict[str, Any]] = []
    filtro_lower = (filtro_nome or "").strip().lower()
    for canon, entry in indice.items():
        if filtro_lower:
            match_nome = filtro_lower in canon.lower()
            match_aliases = any(filtro_lower in (a or "").lower() for a in entry.get("aliases", []))
            if not match_nome and not match_aliases:
                continue
        size_b = entry.get("size_bytes")
        if size_b is None:
            try:
                p = entry.get("path", "")
                size_b = os.path.getsize(p) if p and os.path.isfile(p) else 0
            except (OSError, PermissionError):
                size_b = 0
        lista.append({
            "nome_canonico": canon,
            "path": entry.get("path", ""),
            "type": entry.get("type", ""),
            "source": entry.get("source", ""),
            "size_bytes": size_b,
            "tamanho_formatado": _formatar_tamanho(size_b),
        })
    # Ordenação
    key_map = {
        "nome": lambda x: (x["nome_canonico"] or "").lower(),
        "tamanho": lambda x: x.get("size_bytes") or 0,
        "origem": lambda x: (x.get("source") or "").lower(),
        "tipo": lambda x: (x.get("type") or "").lower(),
    }
    key_fn = key_map.get(ordenar_por, key_map["nome"])
    lista.sort(key=key_fn, reverse=not ordem_asc)
    return lista[: max(1, int(limite))]
