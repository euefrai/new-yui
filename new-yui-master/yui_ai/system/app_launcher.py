"""
Engine profissional de abertura de aplicativos no Windows.

Estratégia (em ordem):
1. subprocess.run([nome])
2. os.startfile(nome)
3. Buscar executáveis em Program Files, Program Files (x86), AppData\\Local, AppData\\Roaming
4. Buscar atalhos (.lnk) no Desktop e Menu Iniciar
5. Consultar registro do Windows (App Paths)
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Caminhos padrão Windows
_PROGRAM_FILES = os.environ.get("ProgramFiles", "C:\\Program Files")
_PROGRAM_FILES_X86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
_LOCAL_APPDATA = os.environ.get("LOCALAPPDATA", "")
_ROAMING_APPDATA = os.environ.get("APPDATA", "")
_USERPROFILE = os.environ.get("USERPROFILE", "")
_PUBLIC = os.environ.get("PUBLIC", os.path.expandvars("%PUBLIC%"))


def _normalizar_nome(nome: str) -> str:
    """Remove acentos e deixa minúsculo para comparação."""
    s = (nome or "").strip().lower()
    return s


def _tentar_subprocess(nome: str) -> Optional[str]:
    """Tenta abrir com subprocess.run([nome]). Retorna caminho se existir no PATH."""
    try:
        exe = _which(nome)
        if exe:
            subprocess.Popen([exe], shell=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return exe
    except Exception:
        pass
    try:
        subprocess.Popen([nome], shell=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return nome
    except Exception:
        pass
    return None


def _which(nome: str) -> Optional[str]:
    """Equivalente a shutil.which (disponível em Python 3.3+)."""
    try:
        import shutil
        return shutil.which(nome)
    except Exception:
        pass
    pathext = os.environ.get("PATHEXT", ".EXE;.COM;.BAT;.CMD").split(";")
    path = os.environ.get("PATH", "").split(os.pathsep)
    for p in path:
        base = os.path.join(p, nome)
        for ext in pathext:
            if os.path.isfile(base + ext):
                return base + ext
        if os.path.isfile(base):
            return base
    return None


def _tentar_startfile(nome: str) -> bool:
    """Tenta os.startfile(nome)."""
    try:
        if os.path.isfile(nome) or os.path.isdir(nome):
            os.startfile(nome)
            return True
    except Exception:
        pass
    return False


def _buscar_executaveis_em_pasta(pasta: str, nome_base: str, profundidade: int = 2) -> Optional[str]:
    """Busca executável por nome em uma pasta (limitado por profundidade)."""
    if not pasta or not os.path.isdir(pasta):
        return None
    nome_base_lower = nome_base.lower().strip()
    nome_exe = nome_base_lower if nome_base_lower.endswith(".exe") else nome_base_lower + ".exe"
    try:
        for root, _dirs, files in os.walk(pasta):
            rel = os.path.relpath(root, pasta)
            if rel.count(os.sep) >= profundidade:
                _dirs.clear()
                continue
            for f in files:
                if not f.lower().endswith(".exe"):
                    continue
                fl = f.lower()
                fn = fl.replace(".exe", "")
                if fl == nome_exe:
                    return os.path.join(root, f)
                if fn.startswith(nome_base_lower + " ") or nome_base_lower in fn:
                    return os.path.join(root, f)
    except Exception:
        pass
    return None


def _buscar_em_pastas_conhecidas(nome: str) -> Optional[str]:
    """Busca em Program Files, Program Files (x86), AppData\\Local, AppData\\Roaming."""
    base = nome.replace(".exe", "").replace(" ", "").lower()
    primeiro_termo = nome.split()[0].lower() if nome.strip() else base
    candidatos = [base, primeiro_termo, nome.replace(".exe", "")]
    pastas = [_PROGRAM_FILES, _PROGRAM_FILES_X86]
    if _LOCAL_APPDATA:
        pastas.append(_LOCAL_APPDATA)
    if _ROAMING_APPDATA:
        pastas.append(_ROAMING_APPDATA)
    for pasta in pastas:
        for cand in candidatos:
            c = cand.replace(".exe", "").strip()
            if not c:
                continue
            exe = _buscar_executaveis_em_pasta(pasta, c, 3)
            if exe:
                return exe
    return None


def _resolver_lnk(caminho_lnk: str) -> Optional[str]:
    """Resolve atalho .lnk no Windows (lê o target)."""
    if not caminho_lnk.lower().endswith(".lnk"):
        return None
    try:
        import struct
        with open(caminho_lnk, "rb") as f:
            content = f.read()
        if content[:4] != b"L\x00\x00\x00":
            return None
        ofs = 0x4C
        flags = struct.unpack("<I", content[0x14:0x18])[0]
        if flags & 1:
            ofs += 0x60
        pos = content.find(b"\x00\x00\x00", ofs)
        if pos == -1:
            return None
        s = content[ofs:pos].decode("utf-16-le", errors="ignore").strip()
        if s and os.path.exists(s):
            return s
    except Exception:
        pass
    return None


def _buscar_atalhos(nome: str) -> Optional[str]:
    """Busca .lnk no Desktop e Menu Iniciar."""
    nome_lower = _normalizar_nome(nome)
    pastas = []
    if _USERPROFILE:
        pastas.append(os.path.join(_USERPROFILE, "Desktop"))
        pastas.append(os.path.join(_USERPROFILE, "AppData", "Roaming", "Microsoft", "Windows", "Start Menu"))
    if _PUBLIC:
        pastas.append(os.path.join(_PUBLIC, "Desktop"))
        pastas.append(os.path.join(_PUBLIC, "Microsoft", "Windows", "Start Menu"))
    for pasta in pastas:
        if not os.path.isdir(pasta):
            continue
        try:
            for f in os.listdir(pasta):
                if not f.lower().endswith(".lnk"):
                    continue
                base = f[:-4].lower()
                if nome_lower in base or base in nome_lower:
                    path_lnk = os.path.join(pasta, f)
                    target = _resolver_lnk(path_lnk)
                    if target:
                        return target
                    try:
                        os.startfile(path_lnk)
                        return path_lnk
                    except Exception:
                        pass
        except Exception:
            pass
    return None


def _buscar_registro_app_paths(nome: str) -> Optional[str]:
    """Consulta App Paths no registro do Windows."""
    if sys.platform != "win32":
        return None
    try:
        import winreg
        key_name = nome + ".exe" if not nome.lower().endswith(".exe") else nome
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\%s" % key_name
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                key = winreg.OpenKey(hive, key_path, 0, winreg.KEY_READ)
                val, _ = winreg.QueryValueEx(key, "")
                winreg.CloseKey(key)
                if val and os.path.isfile(val):
                    return val
            except WindowsError:
                continue
    except Exception:
        pass
    return None


# Navegadores a tentar em ordem quando o usuário pedir "abrir navegador"
_NAVEGADORES_ORDEM = ["chrome", "google chrome", "brave", "edge", "msedge", "firefox"]

# Aliases comuns para nomes de aplicativos
_ALIASES = {
    "navegador": "navegador",
    "browser": "navegador",
    "internet": "navegador",
    "chrome": "google chrome",
    "google chrome": "chrome",
    "vscode": "visual studio code",
    "vs code": "visual studio code",
    "visual studio code": "code",
    "code": "code",
    "spotify": "spotify",
    "steam": "steam",
    "discord": "discord",
    "brave": "brave",
    "firefox": "firefox",
    "edge": "msedge",
    "notepad": "notepad",
    "calc": "calc",
    "calculadora": "calc",
    "telegram": "telegram",
    "telegram desktop": "telegram",
    "telegramdesktop": "telegram",
}


def _tentar_abrir_qualquer_navegador() -> Optional[str]:
    """Tenta abrir o primeiro navegador disponível (Chrome, Brave, Edge, Firefox). Retorna o nome do que abriu ou None."""
    try:
        from yui_ai.system.app_indexer import search_index
        for nome_nav in _NAVEGADORES_ORDEM:
            entry = search_index(nome_nav)
            if entry:
                path_abrir = entry.get("path")
                if path_abrir and os.path.exists(path_abrir):
                    try:
                        subprocess.Popen(
                            [path_abrir],
                            shell=False,
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        return nome_nav
                    except Exception:
                        pass
    except Exception:
        pass
    for nome_nav in _NAVEGADORES_ORDEM:
        exe = _tentar_subprocess(nome_nav)
        if exe:
            return nome_nav
        exe = _buscar_em_pastas_conhecidas(nome_nav)
        if exe:
            try:
                subprocess.Popen([exe], shell=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return nome_nav
            except Exception:
                pass
        lnk = _buscar_atalhos(nome_nav)
        if lnk:
            try:
                if lnk.lower().endswith(".lnk"):
                    os.startfile(lnk)
                else:
                    subprocess.Popen([lnk], shell=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return nome_nav
            except Exception:
                pass
    return None


def abrir_aplicativo(nome_aplicativo: str) -> Dict:
    """
    Abre um aplicativo no Windows.

    Retorna dict no padrão das ações:
    - ok: bool
    - mensagem: str
    - codigo: str (em caso de falha)
    - dados: dict opcional (ex.: caminho aberto)
    """
    nome = (nome_aplicativo or "").strip()
    if not nome:
        return {"ok": False, "mensagem": "Nome do aplicativo não informado.", "codigo": "DADO_INVALIDO"}

    nome_normalizado = _normalizar_nome(nome)
    nome_resolver = _ALIASES.get(nome_normalizado, nome_normalizado)

    # 0) "Abrir navegador" — tenta qualquer um disponível (Chrome, Brave, Edge, Firefox)
    if nome_resolver == "navegador":
        aberto = _tentar_abrir_qualquer_navegador()
        if aberto:
            return {"ok": True, "mensagem": f"Abrindo {aberto.title()} 🚀", "dados": {"navegador": aberto}}
        return {
            "ok": False,
            "mensagem": "Nenhum navegador encontrado (Chrome, Brave, Edge ou Firefox). Instale um ou diga o nome, ex.: abrir chrome.",
            "codigo": "NAVEGADOR_NAO_ENCONTRADO",
            "dados": {},
        }

    # 2) Índice de aplicativos (app_index.json) — consulta primeiro
    try:
        from yui_ai.system.app_indexer import search_index
        entry = search_index(nome_normalizado) or search_index(nome_resolver) or search_index(nome)
        if entry:
            path_abrir = entry.get("path")
            if path_abrir and os.path.exists(path_abrir):
                try:
                    if (path_abrir or "").lower().endswith(".lnk"):
                        os.startfile(path_abrir)
                    else:
                        subprocess.Popen(
                            [path_abrir],
                            shell=False,
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                    return {"ok": True, "mensagem": f"Abrindo {nome.title()} 🚀", "dados": {"caminho": path_abrir}}
                except Exception:
                    pass
    except Exception:
        pass

    # 3) subprocess / PATH
    exe = _tentar_subprocess(nome_resolver) or _tentar_subprocess(nome)
    if exe:
        return {"ok": True, "mensagem": f"Abrindo {nome.title()} 🚀", "dados": {"caminho": exe}}

    # 4) startfile (caminho absoluto)
    if os.path.isfile(nome) or os.path.isdir(nome):
        if _tentar_startfile(nome):
            return {"ok": True, "mensagem": f"Abrindo {nome} 🚀", "dados": {"caminho": nome}}

    # 4.5) Caminhos conhecidos no Windows (ex.: Telegram Desktop)
    if nome_normalizado in ("telegram", "telegram desktop") and _LOCAL_APPDATA:
        for sub in ("Programs\\Telegram Desktop\\Telegram.exe", "Programs\\Telegram\\Telegram.exe"):
            exe_known = os.path.join(_LOCAL_APPDATA, sub)
            if os.path.isfile(exe_known):
                try:
                    subprocess.Popen([exe_known], shell=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return {"ok": True, "mensagem": f"Abrindo {nome.title()} 🚀", "dados": {"caminho": exe_known}}
                except Exception:
                    pass

    # 3) Buscar em pastas conhecidas
    exe = _buscar_em_pastas_conhecidas(nome_resolver) or _buscar_em_pastas_conhecidas(nome)
    if exe:
        try:
            subprocess.Popen([exe], shell=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {"ok": True, "mensagem": f"Abrindo {nome.title()} 🚀", "dados": {"caminho": exe}}
        except Exception:
            pass

    # 6) Atalhos .lnk
    lnk = _buscar_atalhos(nome_resolver) or _buscar_atalhos(nome)
    if lnk:
        try:
            if lnk.lower().endswith(".lnk"):
                os.startfile(lnk)
            else:
                subprocess.Popen([lnk], shell=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {"ok": True, "mensagem": f"Abrindo {nome.title()} 🚀", "dados": {"caminho": lnk}}
        except Exception:
            pass

    # 7) Registro App Paths
    exe = _buscar_registro_app_paths(nome_resolver) or _buscar_registro_app_paths(nome)
    if exe:
        try:
            subprocess.Popen([exe], shell=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {"ok": True, "mensagem": f"Abrindo {nome.title()} 🚀", "dados": {"caminho": exe}}
        except Exception:
            pass

    return {
        "ok": False,
        "mensagem": f"Não encontrei o aplicativo '{nome}'. Atualize o índice com 'atualizar lista de aplicativos' ou diga o nome exato.",
        "codigo": "APP_NAO_ENCONTRADO",
        "dados": {"nome_solicitado": nome},
    }
