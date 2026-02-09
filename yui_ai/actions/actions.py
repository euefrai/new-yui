import subprocess
import os
import shutil
import webbrowser
from pathlib import Path
from urllib.parse import quote
import zipfile
import fnmatch
import csv
import io

# pyautogui é opcional (automação de teclado/mouse)
try:
    import pyautogui  # type: ignore
except Exception:  # noqa: BLE001
    pyautogui = None

# Exclusão segura (Lixeira) é opcional
try:
    from send2trash import send2trash  # type: ignore
except Exception:  # noqa: BLE001
    send2trash = None

try:
    from yui_ai.system.logger import log_error
except Exception:  # noqa: BLE001
    def log_error(e, ctx=None):  # type: ignore
        pass

# =============================================================
# PADRÃO DE RETORNO
# =============================================================
def sucesso(msg, dados=None):
    return {
        "ok": True,
        "mensagem": msg,
        "codigo": "SUCESSO",
        "dados": dados or {}
    }

def falha(msg, codigo):
    return {
        "ok": False,
        "mensagem": msg,
        "codigo": codigo
    }

# =============================================================
# MAPA DE EXECUTÁVEIS (WINDOWS)
# =============================================================
APP_PATHS = {
    "brave": [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe"
    ],
    "chrome": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ],
    "edge": [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    ],
    "firefox": [
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe"
    ],
    "excel": [
        r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE"
    ],
    "discord": [
        os.path.expandvars(r"%LOCALAPPDATA%\Discord\Update.exe")
    ]
}

# =============================================================
# ALIASES SEMÂNTICOS
# =============================================================
ALIASES = {
    "google": "chrome",
    "navegador": "chrome",
    "internet": "chrome",
    "msedge": "edge"
}

# =============================================================
# UTILITÁRIOS
# =============================================================
def _abrir_por_caminho(nome):
    caminhos = APP_PATHS.get(nome, [])

    for caminho in caminhos:
        if os.path.exists(caminho):
            # Caso especial: Discord
            if nome == "discord":
                subprocess.Popen(
                    [caminho, "--processStart", "Discord.exe"],
                    shell=False
                )
            else:
                subprocess.Popen([caminho], shell=False)

            return True
    return False


def _abrir_por_path(nome):
    exe = shutil.which(nome)
    if exe:
        subprocess.Popen([exe], shell=False)
        return True
    return False


def _abrir_url_ou_arquivo(alvo):
    try:
        os.startfile(alvo)
        return True
    except Exception:
        return False


def _resolver_caminho(caminho: str) -> str:
    """
    Normaliza e resolve caminhos:
    - remove aspas
    - expande %VAR% e ~
    - resolve relativo para absoluto
    """
    if not caminho:
        return ""

    p = str(caminho).strip().strip('"').strip("'").strip()
    p = os.path.expandvars(p)
    p = os.path.expanduser(p)

    try:
        # resolve relativo ao cwd
        p = str(Path(p).resolve())
    except Exception:
        p = os.path.abspath(p)

    return p

# =============================================================
# AÇÕES
# =============================================================
def abrir_app(nome):
    nome = nome.lower().strip()
    if not nome:
        return falha("Nome do app não informado", "DADO_INVALIDO")

    nome = ALIASES.get(nome, nome)

    # 1️⃣ PATH do sistema
    if _abrir_por_path(nome):
        return sucesso(f"Abrindo {nome}")

    # 2️⃣ Caminhos conhecidos
    if _abrir_por_caminho(nome):
        return sucesso(f"Abrindo {nome}")

    return falha(f"Não encontrei o aplicativo '{nome}'", "APP_NAO_ENCONTRADO")


def abrir_explorador():
    try:
        subprocess.Popen("explorer", shell=True)
        return sucesso("Explorador de arquivos aberto")
    except Exception as e:
        log_error(e, {"codigo": "ERRO_EXECUCAO"})
        return falha(str(e), "ERRO_EXECUCAO")


def _normalizar_url(alvo: str) -> str:
    """Se não tiver esquema, adiciona https://."""
    s = (alvo or "").strip()
    if not s:
        return ""
    s = s.strip('"').strip("'")
    if not s:
        return ""
    lower = s.lower()
    if lower.startswith("http://") or lower.startswith("https://"):
        return s
    return "https://" + s


def abrir_url(url: str):
    """Abre uma URL no navegador padrão."""
    url_norm = _normalizar_url(url)
    if not url_norm:
        return falha("URL ou site não informado.", "DADO_INVALIDO")
    try:
        webbrowser.open(url_norm)
        return sucesso(f"Abrindo {url_norm} no navegador.", {"url": url_norm})
    except Exception as e:
        log_error(e, {"codigo": "ERRO_ABRIR_URL"})
        return falha(str(e), "ERRO_ABRIR_URL")


def pesquisar_no_navegador(termo: str):
    """Abre o navegador padrão com uma pesquisa no Google."""
    termo = (termo or "").strip()
    if not termo:
        return falha("O que você quer pesquisar? Exemplo: pesquisar clima em São Paulo.", "DADO_INVALIDO")
    try:
        url_busca = "https://www.google.com/search?q=" + quote(termo, safe="")
        webbrowser.open(url_busca)
        return sucesso(f"Pesquisando '{termo}' no navegador.", {"url": url_busca, "termo": termo})
    except Exception as e:
        log_error(e, {"codigo": "ERRO_PESQUISA"})
        return falha(str(e), "ERRO_PESQUISA")


def pressionar_tecla(tecla):
    if not tecla:
        return falha("Tecla não informada", "DADO_INVALIDO")

    if pyautogui is None:
        return falha(
            "Automação indisponível (pyautogui não instalado).",
            "DEPENDENCIA_FALTANDO"
        )

    try:
        pyautogui.press(tecla)
        return sucesso(f"Tecla '{tecla}' pressionada")
    except Exception as e:
        log_error(e, {"codigo": "ERRO_AUTOMACAO"})
        return falha(str(e), "ERRO_AUTOMACAO")


def abrir_qualquer_coisa(alvo):
    if not alvo:
        return falha("Alvo não informado", "DADO_INVALIDO")

    alvo = alvo.lower().strip()
    alvo = ALIASES.get(alvo, alvo)

    # 0️⃣ Apps por protocolo (Windows)
    if alvo in ["whatsapp", "wpp", "zap", "zapzap"]:
        try:
            os.startfile("whatsapp:")
            return sucesso("Abrindo whatsapp")
        except Exception:
            # segue para as outras tentativas
            pass

    # 1️⃣ tenta como app
    if _abrir_por_path(alvo) or _abrir_por_caminho(alvo):
        return sucesso(f"Abrindo {alvo}")

    # 2️⃣ tenta como URL / arquivo / pasta
    if _abrir_url_ou_arquivo(alvo):
        return sucesso(f"Abrindo {alvo}")

    return falha(f"Não consegui abrir '{alvo}'", "ERRO_ABERTURA")


def abrir_caminho(caminho: str):
    caminho_resolvido = _resolver_caminho(caminho)
    if not caminho_resolvido:
        return falha("Caminho não informado", "DADO_INVALIDO")

    if not os.path.exists(caminho_resolvido):
        return falha(f"Não encontrei: {caminho_resolvido}", "CAMINHO_NAO_EXISTE")

    if _abrir_url_ou_arquivo(caminho_resolvido):
        return sucesso(f"Abrindo {caminho_resolvido}", {"caminho": caminho_resolvido})

    return falha(f"Não consegui abrir: {caminho_resolvido}", "ERRO_ABERTURA")


def listar_diretorio(caminho: str, limite: int = 20):
    caminho_resolvido = _resolver_caminho(caminho)
    if not caminho_resolvido:
        return falha("Caminho não informado", "DADO_INVALIDO")

    if not os.path.isdir(caminho_resolvido):
        return falha(f"Não é uma pasta: {caminho_resolvido}", "NAO_E_PASTA")

    try:
        itens = sorted(os.listdir(caminho_resolvido))
        itens_limitados = itens[: max(1, int(limite or 20))]
        return sucesso(
            f"Listando itens em {caminho_resolvido}",
            {"caminho": caminho_resolvido, "itens": itens_limitados, "total": len(itens)}
        )
    except Exception as e:
        log_error(e, {"codigo": "ERRO_LISTAGEM"})
        return falha(str(e), "ERRO_LISTAGEM")


def criar_pasta(caminho: str):
    caminho_resolvido = _resolver_caminho(caminho)
    if not caminho_resolvido:
        return falha("Caminho não informado", "DADO_INVALIDO")

    try:
        os.makedirs(caminho_resolvido, exist_ok=True)
        return sucesso("Pasta criada", {"caminho": caminho_resolvido})
    except Exception as e:
        log_error(e, {"codigo": "ERRO_CRIAR_PASTA"})
        return falha(str(e), "ERRO_CRIAR_PASTA")


def mover_caminho(origem: str, destino: str):
    src = _resolver_caminho(origem)
    dst = _resolver_caminho(destino)

    if not src or not dst:
        return falha("Origem/destino não informados", "DADO_INVALIDO")

    if not os.path.exists(src):
        return falha(f"Origem não existe: {src}", "ORIGEM_NAO_EXISTE")

    try:
        # se destino é uma pasta existente, move para dentro dela
        if os.path.isdir(dst):
            dst_final = os.path.join(dst, os.path.basename(src))
        else:
            dst_final = dst
            os.makedirs(os.path.dirname(dst_final) or ".", exist_ok=True)

        resultado = shutil.move(src, dst_final)
        return sucesso("Movido com sucesso", {"origem": src, "destino": resultado})
    except Exception as e:
        log_error(e, {"codigo": "ERRO_MOVER"})
        return falha(str(e), "ERRO_MOVER")


def copiar_caminho(origem: str, destino: str):
    src = _resolver_caminho(origem)
    dst = _resolver_caminho(destino)

    if not src or not dst:
        return falha("Origem/destino não informados", "DADO_INVALIDO")

    if not os.path.exists(src):
        return falha(f"Origem não existe: {src}", "ORIGEM_NAO_EXISTE")

    try:
        if os.path.isdir(src):
            # se destino é pasta existente, copia para dentro dela com mesmo nome
            if os.path.isdir(dst):
                dst_final = os.path.join(dst, os.path.basename(src))
            else:
                dst_final = dst
                os.makedirs(os.path.dirname(dst_final) or ".", exist_ok=True)

            shutil.copytree(src, dst_final, dirs_exist_ok=True)
            return sucesso("Pasta copiada com sucesso", {"origem": src, "destino": dst_final})

        # arquivo
        if os.path.isdir(dst):
            dst_final = os.path.join(dst, os.path.basename(src))
        else:
            dst_final = dst
            os.makedirs(os.path.dirname(dst_final) or ".", exist_ok=True)

        shutil.copy2(src, dst_final)
        return sucesso("Arquivo copiado com sucesso", {"origem": src, "destino": dst_final})
    except Exception as e:
        log_error(e, {"codigo": "ERRO_COPIAR"})
        return falha(str(e), "ERRO_COPIAR")


def excluir_caminho(caminho: str, definitivo: bool = False):
    alvo = _resolver_caminho(caminho)
    if not alvo:
        return falha("Caminho não informado", "DADO_INVALIDO")

    if not os.path.exists(alvo):
        return falha(f"Não encontrei: {alvo}", "CAMINHO_NAO_EXISTE")

    # padrão: mandar pra Lixeira (mais seguro)
    if not definitivo:
        if send2trash is None:
            return falha(
                "Exclusão segura indisponível (instale send2trash em requirements-automation.txt).",
                "DEPENDENCIA_FALTANDO"
            )
        try:
            send2trash(alvo)
            return sucesso("Enviado para a Lixeira", {"caminho": alvo})
        except Exception as e:
            log_error(e, {"codigo": "ERRO_LIXEIRA"})
            return falha(str(e), "ERRO_LIXEIRA")

    # definitivo (perigoso)
    try:
        if os.path.isdir(alvo):
            shutil.rmtree(alvo)
        else:
            os.remove(alvo)
        return sucesso("Excluído definitivamente", {"caminho": alvo})
    except Exception as e:
        log_error(e, {"codigo": "ERRO_EXCLUIR"})
        return falha(str(e), "ERRO_EXCLUIR")


def renomear_caminho(origem: str, novo_nome_ou_caminho: str):
    src = _resolver_caminho(origem)
    dst_raw = (novo_nome_ou_caminho or "").strip().strip('"').strip("'").strip()
    if not src or not dst_raw:
        return falha("Origem/novo nome não informados", "DADO_INVALIDO")

    if not os.path.exists(src):
        return falha(f"Origem não existe: {src}", "ORIGEM_NAO_EXISTE")

    # Se o destino não tiver drive/dir, trata como "novo nome" no mesmo diretório
    dst = _resolver_caminho(dst_raw)
    try:
        # heurística: se o usuário passou só "arquivo.txt"
        if os.path.basename(dst_raw) == dst_raw and (":" not in dst_raw) and ("/" not in dst_raw) and ("\\" not in dst_raw):
            dst = os.path.join(os.path.dirname(src), dst_raw)

        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        os.replace(src, dst)
        return sucesso("Renomeado com sucesso", {"origem": src, "destino": dst})
    except Exception as e:
        log_error(e, {"codigo": "ERRO_RENOMEAR"})
        return falha(str(e), "ERRO_RENOMEAR")


def ler_arquivo_texto(caminho: str, max_chars: int = 4000):
    p = _resolver_caminho(caminho)
    if not p:
        return falha("Caminho não informado", "DADO_INVALIDO")

    if not os.path.exists(p):
        return falha(f"Não encontrei: {p}", "CAMINHO_NAO_EXISTE")

    if os.path.isdir(p):
        return falha("Caminho é uma pasta, não um arquivo", "NAO_E_ARQUIVO")

    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            conteudo = f.read(int(max_chars or 4000))
        return sucesso("Conteúdo lido", {"caminho": p, "conteudo": conteudo, "truncado": len(conteudo) >= int(max_chars or 4000)})
    except Exception as e:
        log_error(e, {"codigo": "ERRO_LER_ARQUIVO"})
        return falha(str(e), "ERRO_LER_ARQUIVO")


def escrever_arquivo_texto(caminho: str, texto: str, modo: str = "sobrescrever"):
    """
    modo:
      - sobrescrever
      - anexar
    """
    p = _resolver_caminho(caminho)
    if not p:
        return falha("Caminho não informado", "DADO_INVALIDO")

    texto = texto or ""
    try:
        os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
        file_mode = "a" if modo == "anexar" else "w"
        with open(p, file_mode, encoding="utf-8") as f:
            f.write(texto)
        return sucesso("Arquivo escrito", {"caminho": p, "modo": modo, "chars": len(texto)})
    except Exception as e:
        log_error(e, {"codigo": "ERRO_ESCREVER_ARQUIVO"})
        return falha(str(e), "ERRO_ESCREVER_ARQUIVO")


def buscar_arquivos(pasta: str, padrao: str = "*", limite: int = 50):
    """
    Busca recursiva simples por padrão (fnmatch), ex:
      - *.pdf
      - *relatorio*
    """
    raiz = _resolver_caminho(pasta)
    if not raiz:
        return falha("Pasta não informada", "DADO_INVALIDO")

    if not os.path.isdir(raiz):
        return falha(f"Não é uma pasta: {raiz}", "NAO_E_PASTA")

    padrao = (padrao or "*").strip()
    max_items = max(1, int(limite or 50))

    encontrados = []
    try:
        for base, _, arquivos in os.walk(raiz):
            for nome in arquivos:
                if fnmatch.fnmatch(nome.lower(), padrao.lower()):
                    encontrados.append(os.path.join(base, nome))
                    if len(encontrados) >= max_items:
                        return sucesso(
                            "Busca concluída (limitada)",
                            {"pasta": raiz, "padrao": padrao, "resultados": encontrados, "limitado": True}
                        )
        return sucesso("Busca concluída", {"pasta": raiz, "padrao": padrao, "resultados": encontrados, "limitado": False})
    except Exception as e:
        log_error(e, {"codigo": "ERRO_BUSCA"})
        return falha(str(e), "ERRO_BUSCA")


def compactar_zip(origem: str, destino_zip: str):
    src = _resolver_caminho(origem)
    dst = _resolver_caminho(destino_zip)

    if not src or not dst:
        return falha("Origem/destino não informados", "DADO_INVALIDO")

    if not os.path.exists(src):
        return falha(f"Origem não existe: {src}", "ORIGEM_NAO_EXISTE")

    if not dst.lower().endswith(".zip"):
        dst = dst + ".zip"

    try:
        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        with zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_DEFLATED) as z:
            if os.path.isdir(src):
                base_dir = os.path.dirname(src)
                for root, _, files in os.walk(src):
                    for file in files:
                        full = os.path.join(root, file)
                        arcname = os.path.relpath(full, base_dir)
                        z.write(full, arcname)
            else:
                z.write(src, os.path.basename(src))
        return sucesso("ZIP criado", {"origem": src, "destino": dst})
    except Exception as e:
        log_error(e, {"codigo": "ERRO_ZIP"})
        return falha(str(e), "ERRO_ZIP")


def extrair_zip(arquivo_zip: str, destino_pasta: str):
    zpath = _resolver_caminho(arquivo_zip)
    dst = _resolver_caminho(destino_pasta)

    if not zpath or not dst:
        return falha("ZIP/destino não informados", "DADO_INVALIDO")

    if not os.path.exists(zpath):
        return falha(f"ZIP não existe: {zpath}", "CAMINHO_NAO_EXISTE")

    try:
        os.makedirs(dst, exist_ok=True)
        with zipfile.ZipFile(zpath, "r") as z:
            z.extractall(dst)
        return sucesso("ZIP extraído", {"zip": zpath, "destino": dst})
    except Exception as e:
        log_error(e, {"codigo": "ERRO_UNZIP"})
        return falha(str(e), "ERRO_UNZIP")


def listar_processos(limite: int = 30):
    """
    Windows: usa tasklist /fo csv para listar processos.
    """
    max_items = max(1, int(limite or 30))
    try:
        p = subprocess.run(
            ["tasklist", "/fo", "csv", "/nh"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        if p.returncode != 0:
            return falha(p.stderr.strip() or "Falha ao listar processos", "ERRO_PROCESSOS")

        reader = csv.reader(io.StringIO(p.stdout))
        processos = []
        for row in reader:
            # "Image Name","PID","Session Name","Session#","Mem Usage"
            if not row or len(row) < 2:
                continue
            processos.append({"nome": row[0], "pid": row[1], "memoria": row[4] if len(row) > 4 else ""})
            if len(processos) >= max_items:
                break

        return sucesso("Processos listados", {"processos": processos, "limitado": True})
    except Exception as e:
        log_error(e, {"codigo": "ERRO_PROCESSOS"})
        return falha(str(e), "ERRO_PROCESSOS")


def encerrar_processo(identificador: str, forcar: bool = True):
    """
    identificador: PID (número) ou nome (ex: chrome.exe)
    """
    ident = (identificador or "").strip().strip('"').strip("'").strip()
    if not ident:
        return falha("PID/nome não informado", "DADO_INVALIDO")

    try:
        args = ["taskkill"]
        if ident.isdigit():
            args += ["/PID", ident]
        else:
            # normaliza extensão
            if not ident.lower().endswith(".exe"):
                ident = ident + ".exe"
            args += ["/IM", ident]
        if forcar:
            args.append("/F")
        args.append("/T")

        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p.returncode != 0:
            return falha(p.stderr.strip() or p.stdout.strip() or "Falha ao encerrar processo", "ERRO_ENCERRAR")
        return sucesso("Processo encerrado", {"identificador": ident, "saida": (p.stdout or "").strip()})
    except Exception as e:
        log_error(e, {"codigo": "ERRO_ENCERRAR"})
        return falha(str(e), "ERRO_ENCERRAR")

# =============================================================
# DISPATCHER
# =============================================================
def executar_acao(acao, dados):
    try:
        if acao == "abrir_app":
            nome = dados.get("app") or dados.get("nome", "")
            return abrir_app(nome)

        if acao == "abrir_aplicativo":
            from yui_ai.system.app_launcher import abrir_aplicativo as abrir_app_engine
            resultado = abrir_app_engine(dados.get("nome_aplicativo", ""))
            if resultado.get("ok"):
                return sucesso(resultado.get("mensagem", "Abrindo aplicativo."), resultado.get("dados"))
            return falha(resultado.get("mensagem", "Não foi possível abrir."), resultado.get("codigo", "ERRO_ABERTURA"))

        if acao == "indexar_aplicativos":
            from yui_ai.system.app_indexer import build_index
            ok_index, total, msg = build_index(progress_callback=None)
            if ok_index:
                return sucesso(
                    f"Foram encontrados {total} aplicativos. Índice salvo com sucesso.",
                    {"total": total, "mensagem": msg, "relatorio": f"Total indexado: {total} aplicativos."}
                )
            return falha(msg or "Falha ao indexar aplicativos.", "ERRO_INDEXACAO")

        if acao == "atualizar_indice_aplicativos":
            from yui_ai.system.app_indexer import build_index
            ok_index, total, msg = build_index(progress_callback=None)
            if ok_index:
                return sucesso(
                    f"Foram encontrados {total} aplicativos. Índice salvo com sucesso.",
                    {"total": total, "mensagem": msg, "relatorio": f"Índice atualizado: {total} aplicativos."}
                )
            return falha(msg or "Falha ao atualizar índice.", "ERRO_INDEXACAO")

        if acao == "listar_aplicativos_indexados":
            from yui_ai.system.app_indexer import get_index_path, listar_indexados_com_filtros
            filtro_nome = (dados.get("filtro_nome") or "").strip() or None
            ordenar_por = (dados.get("ordenar_por") or "nome").strip().lower()
            if ordenar_por not in ("nome", "tamanho", "origem", "tipo"):
                ordenar_por = "nome"
            ordem_asc = dados.get("ordem_asc", True)
            limite = max(10, min(500, int(dados.get("limite", 150))))
            lista = listar_indexados_com_filtros(
                filtro_nome=filtro_nome,
                ordenar_por=ordenar_por,
                ordem_asc=ordem_asc,
                limite=limite,
            )
            total = len(lista)
            caminho = get_index_path()
            # Linhas para exibição: nome | tamanho | tipo | origem
            itens = []
            for item in lista:
                nome = item.get("nome_canonico", "")
                tam = item.get("tamanho_formatado", "—")
                tipo = item.get("type", "")
                orig = item.get("source", "")
                itens.append(f"{nome}  |  {tam}  |  {tipo}  |  {orig}")
            if not itens:
                msg = "Nenhum aplicativo encontrado no índice."
                if filtro_nome:
                    msg = f"Nenhum aplicativo encontrado com '{filtro_nome}'. Tente outro filtro ou diga 'atualizar lista de aplicativos'."
                return sucesso(msg, {"total": 0, "visualizacao": msg, "itens": []})
            titulo = f"Lista de aplicativos ({total} itens)"
            if filtro_nome:
                titulo += f" — filtro: '{filtro_nome}'"
            titulo += f" — ordenado por {ordenar_por}"
            cabecalho = "Nome  |  Tamanho  |  Tipo  |  Origem"
            visualizacao = f"{titulo}\n{cabecalho}\n" + "\n".join(itens)
            return sucesso(
                f"Listei {total} aplicativo(s). Índice: {caminho}.",
                {"total": total, "visualizacao": visualizacao, "itens": itens, "lista": lista}
            )

        if acao == "pressionar_tecla":
            return pressionar_tecla(dados.get("tecla", ""))

        if acao == "abrir_explorador":
            return abrir_explorador()

        if acao == "abrir_qualquer_coisa":
            return abrir_qualquer_coisa(dados.get("alvo", ""))

        if acao == "abrir_url":
            return abrir_url(dados.get("url", ""))

        if acao == "pesquisar_no_navegador":
            return pesquisar_no_navegador(dados.get("termo", ""))

        if acao == "abrir_caminho":
            return abrir_caminho(dados.get("caminho", ""))

        if acao == "abrir_pasta_raiz":
            from yui_ai.core.file_resolver import PROJECT_ROOT
            return abrir_caminho(PROJECT_ROOT)

        if acao == "mostrar_estrutura_projeto":
            from yui_ai.core.file_resolver import PROJECT_ROOT
            return listar_diretorio(PROJECT_ROOT, dados.get("limite", 50))

        if acao == "abrir_logs":
            from yui_ai.core.file_resolver import PROJECT_ROOT
            logs_path = os.path.join(PROJECT_ROOT, "logs")
            if os.path.isdir(logs_path):
                return abrir_caminho(logs_path)
            return falha("Pasta 'logs' não encontrada na raiz do projeto.", "PASTA_NAO_EXISTE")

        if acao == "executar_yui":
            return sucesso("Yui já está em execução.", {})

        if acao == "reiniciar_yui":
            return sucesso("Para reiniciar, feche esta janela e execute novamente: python -m yui_ai.", {})

        if acao == "executar_validacao_completa":
            from yui_ai.core.file_resolver import PROJECT_ROOT
            from yui_ai.validation.validation_engine import ValidationEngine
            main_py = os.path.join(PROJECT_ROOT, "yui_ai", "main.py")
            if not os.path.isfile(main_py):
                return falha("Arquivo main.py não encontrado.", "ARQUIVO_NAO_EXISTE")
            v = ValidationEngine()
            res = v.validar_apos_edicao(main_py, PROJECT_ROOT)
            txt = v.formatar_resultado_completo(res)
            return sucesso("Validação executada (somente leitura).", {"relatorio": txt, "resultado": res})

        if acao == "listar_diretorio":
            return listar_diretorio(dados.get("caminho", ""), dados.get("limite", 20))

        if acao == "criar_pasta":
            return criar_pasta(dados.get("caminho", ""))

        if acao == "mover_caminho":
            return mover_caminho(dados.get("origem", ""), dados.get("destino", ""))

        if acao == "copiar_caminho":
            return copiar_caminho(dados.get("origem", ""), dados.get("destino", ""))

        if acao == "excluir_caminho":
            return excluir_caminho(dados.get("caminho", ""), bool(dados.get("definitivo", False)))

        if acao == "renomear_caminho":
            return renomear_caminho(dados.get("origem", ""), dados.get("novo", ""))

        if acao == "ler_arquivo_texto":
            return ler_arquivo_texto(dados.get("caminho", ""), dados.get("max_chars", 4000))

        if acao == "escrever_arquivo_texto":
            return escrever_arquivo_texto(
                dados.get("caminho", ""),
                dados.get("texto", ""),
                dados.get("modo", "sobrescrever")
            )

        if acao == "buscar_arquivos":
            return buscar_arquivos(dados.get("pasta", ""), dados.get("padrao", "*"), dados.get("limite", 50))

        if acao == "compactar_zip":
            return compactar_zip(dados.get("origem", ""), dados.get("destino", ""))

        if acao == "extrair_zip":
            return extrair_zip(dados.get("zip", ""), dados.get("destino", ""))

        if acao == "listar_processos":
            return listar_processos(dados.get("limite", 30))

        if acao == "encerrar_processo":
            return encerrar_processo(dados.get("identificador", ""), bool(dados.get("forcar", True)))

        # =============================
        # ANÁLISE DE PROJETO (SOMENTE LEITURA — NUNCA EDITA, NUNCA PATCH, NUNCA CONFIRMAÇÃO)
        # =============================
        if acao == "analisar_projeto":
            from yui_ai.project_analysis.analysis_report import executar_analise_completa
            sucesso_analise = False
            erro_analise = None
            dados_analise = None
            sucesso_analise, dados_analise, erro_analise = executar_analise_completa(dados.get("raiz"))
            if sucesso_analise and dados_analise is not None:
                return sucesso("Análise concluída (somente leitura)", {
                    "relatorio": dados_analise.get("texto_formatado", ""),
                    "dados_completos": dados_analise,
                })
            return falha(erro_analise or "Erro ao analisar projeto", "ERRO_ANALISE")

        # =============================
        # AÇÕES DE EDIÇÃO DE CÓDIGO (REQUEREM CONFIRMAÇÃO)
        # =============================
        if acao == "preparar_edicao_codigo":
            from yui_ai.actions.code_actions import preparar_edicao_codigo
            return preparar_edicao_codigo(
                dados.get("arquivo", ""),
                dados.get("conteudo_novo", ""),
                dados.get("descricao", "")
            )

        if acao == "aplicar_edicao_codigo":
            from yui_ai.actions.code_actions import aplicar_edicao_codigo
            patch = dados.get("patch")
            if not patch:
                return falha("Patch não fornecido", "DADO_INVALIDO")
            return aplicar_edicao_codigo(patch, bool(dados.get("validar", True)))

        if acao == "visualizar_edicoes_pendentes":
            from yui_ai.actions.code_actions import visualizar_edicoes_pendentes
            return visualizar_edicoes_pendentes()

        if acao == "reverter_edicao_codigo":
            from yui_ai.actions.code_actions import reverter_edicao_codigo
            return reverter_edicao_codigo(
                dados.get("arquivo", ""),
                dados.get("entrada_id")
            )

        if acao == "obter_historico_edicoes":
            from yui_ai.actions.code_actions import obter_historico_edicoes
            return obter_historico_edicoes(
                dados.get("arquivo"),
                dados.get("limite", 10)
            )

        # =============================
        # GERAÇÃO DE CÓDIGO VIA IA (NUNCA APLICA DIRETAMENTE)
        # =============================
        if acao == "gerar_codigo_refatorado":
            from yui_ai.code_editor.code_generator import gerar_codigo_refatorado
            ok_ref, resultado, err_ref = gerar_codigo_refatorado(
                dados.get("arquivo", ""),
                dados.get("instrucao", ""),
                dados.get("contexto_adicional", "")
            )
            if ok_ref:
                return sucesso(
                    "Código refatorado gerado (aguardando confirmação)",
                    resultado
                )
            return falha(err_ref or "Falha ao gerar código", "ERRO_GERAR_CODIGO")

        if acao == "analisar_e_corrigir_bug":
            from yui_ai.code_editor.code_generator import analisar_e_sugerir_correcao
            ok_corr, resultado, err_corr = analisar_e_sugerir_correcao(
                dados.get("arquivo", ""),
                dados.get("descricao_bug", "")
            )
            if ok_corr:
                return sucesso(
                    "Correção de bug gerada (aguardando confirmação)",
                    resultado
                )
            return falha(err_corr or "Falha ao analisar código", "ERRO_ANALISAR_CODIGO")

        # =============================
        # MEMÓRIA ARQUITETURAL E REGRAS
        # =============================
        if acao == "registrar_regra_arquitetural":
            from yui_ai.actions.architecture_actions import registrar_regra_arquitetural
            return registrar_regra_arquitetural(
                dados.get("comando_completo", ""),
                dados.get("tipo", ""),
                dados.get("conteudo", "")
            )

        if acao == "confirmar_registro_regra":
            from yui_ai.actions.architecture_actions import confirmar_registro_regra
            return confirmar_registro_regra(
                dados.get("entrada", {}),
                dados.get("tipo", "")
            )

        if acao == "consultar_regras":
            from yui_ai.actions.architecture_actions import consultar_regras
            return consultar_regras(dados.get("filtro", ""))

        if acao == "consultar_padroes":
            from yui_ai.actions.architecture_actions import consultar_padroes
            return consultar_padroes(dados.get("filtro", ""))

        if acao == "consultar_memoria_arquitetural":
            from yui_ai.actions.architecture_actions import consultar_memoria_arquitetural
            return consultar_memoria_arquitetural()

        return falha(f"Ação '{acao}' não reconhecida", "ACAO_DESCONHECIDA")

    except Exception as e:
        log_error(e, {"codigo": "ERRO_CRITICO"})
        return falha(str(e), "ERRO_CRITICO")
