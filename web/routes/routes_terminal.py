"""
Terminal WebSocket — conecta xterm.js ao shell do servidor.
Um PTY por conexão; cwd = sandbox.
Linux/macOS: PTY. Windows: subprocess (sem PTY).
Kill Switch: processos sem interação > 2 min são encerrados.
"""

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from flask_sock import Sock

try:
    from config import settings
    SANDBOX_DIR = Path(settings.SANDBOX_DIR).resolve()
except Exception:
    SANDBOX_DIR = Path(__file__).resolve().parents[2] / "sandbox"

sock = Sock()

# Registro de processos ativos: {id: {proc, master, use_pty, last_activity}}
_terminal_processes: dict = {}
_terminal_lock = threading.Lock()
_terminal_counter = 0

IDLE_KILL_SECONDS = 120  # 2 minutos sem interação


def cleanup_processes():
    """Encerra processos de terminal sem interação há mais de 2 minutos."""
    now = time.time()
    to_remove = []
    with _terminal_lock:
        for tid, info in list(_terminal_processes.items()):
            if now - info.get("last_activity", 0) > IDLE_KILL_SECONDS:
                to_remove.append(tid)
    for tid in to_remove:
        with _terminal_lock:
            info = _terminal_processes.pop(tid, None)
        if info:
            proc = info.get("proc")
            master = info.get("master")
            try:
                if proc and proc.poll() is None:
                    proc.terminate()
                    proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            if master is not None:
                try:
                    os.close(master)
                except Exception:
                    pass
    try:
        from core.system_state import set_terminal_sessions_alive
        with _terminal_lock:
            set_terminal_sessions_alive(len(_terminal_processes) > 0)
    except Exception:
        pass


def _spawn_shell():
    """Spawna shell no sandbox. Usa PTY no Unix, subprocess no Windows."""
    cwd = str(SANDBOX_DIR)
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    if sys.platform == "win32":
        proc = subprocess.Popen(
            ["cmd.exe", "/K"],
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=False,
        )
        return proc, None, False
    try:
        import pty
        master, slave = pty.openpty()
        proc = subprocess.Popen(
            ["bash", "-l"],
            cwd=cwd,
            env=env,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            preexec_fn=os.setsid if hasattr(os, "setsid") else None,
        )
        os.close(slave)
        return proc, master, True
    except Exception:
        proc = subprocess.Popen(
            ["bash", "-l"],
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        return proc, None, False


def _run_reader(ws, proc, master, use_pty):
    """Thread: lê da saída e envia ao WebSocket."""
    try:
        if use_pty and master is not None:
            import select
            while proc.poll() is None:
                r, _, _ = select.select([master], [], [], 0.1)
                if r:
                    try:
                        data = os.read(master, 4096)
                        if data:
                            ws.send(data.decode("utf-8", errors="replace"))
                    except (OSError, UnicodeDecodeError):
                        break
        elif proc.stdout:
            while proc.poll() is None:
                try:
                    data = proc.stdout.read(4096)
                    if data:
                        ws.send(data.decode("utf-8", errors="replace"))
                except Exception:
                    break
    except Exception:
        pass


def _cleanup_loop():
    """Thread que chama cleanup_processes a cada 60 segundos."""
    while True:
        time.sleep(60)
        try:
            cleanup_processes()
        except Exception:
            pass


def register_terminal_sock(app, sock_instance):
    """Registra a rota WebSocket do terminal."""
    threading.Thread(target=_cleanup_loop, daemon=True).start()

    @sock_instance.route("/ws/terminal")
    def terminal_ws(ws):
        global _terminal_counter
        proc, master, use_pty = _spawn_shell()
        with _terminal_lock:
            _terminal_counter += 1
            tid = _terminal_counter
            _terminal_processes[tid] = {
                "proc": proc,
                "master": master,
                "use_pty": use_pty,
                "last_activity": time.time(),
            }
        try:
            from core.system_state import set_terminal_sessions_alive
            set_terminal_sessions_alive(True)
        except Exception:
            pass
        try:
            t = threading.Thread(target=_run_reader, args=(ws, proc, master, use_pty), daemon=True)
            t.start()
            while True:
                try:
                    msg = ws.receive()
                    if msg is None:
                        break
                    with _terminal_lock:
                        if tid in _terminal_processes:
                            _terminal_processes[tid]["last_activity"] = time.time()
                    if use_pty and master is not None:
                        os.write(master, msg.encode("utf-8", errors="replace"))
                    elif proc.stdin:
                        proc.stdin.write(msg.encode("utf-8", errors="replace"))
                        proc.stdin.flush()
                except Exception:
                    break
        finally:
            with _terminal_lock:
                _terminal_processes.pop(tid, None)
                alive = len(_terminal_processes) > 0
            try:
                from core.system_state import set_terminal_sessions_alive
                set_terminal_sessions_alive(alive)
            except Exception:
                pass
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            if master is not None:
                try:
                    os.close(master)
                except Exception:
                    pass
