"""
Terminal WebSocket — conecta xterm.js ao shell do servidor.
Um PTY por conexão; cwd = sandbox.
Linux/macOS: PTY. Windows: subprocess (sem PTY).
"""

import os
import subprocess
import sys
import threading
from pathlib import Path

from flask_sock import Sock

try:
    from config import settings
    SANDBOX_DIR = Path(settings.SANDBOX_DIR).resolve()
except Exception:
    SANDBOX_DIR = Path(__file__).resolve().parents[2] / "sandbox"

sock = Sock()


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


def register_terminal_sock(app, sock_instance):
    """Registra a rota WebSocket do terminal."""
    @sock_instance.route("/ws/terminal")
    def terminal_ws(ws):
        proc, master, use_pty = _spawn_shell()
        try:
            t = threading.Thread(target=_run_reader, args=(ws, proc, master, use_pty), daemon=True)
            t.start()
            while True:
                try:
                    msg = ws.receive()
                    if msg is None:
                        break
                    if use_pty and master is not None:
                        os.write(master, msg.encode("utf-8", errors="replace"))
                    elif proc.stdin:
                        proc.stdin.write(msg.encode("utf-8", errors="replace"))
                        proc.stdin.flush()
                except Exception:
                    break
        finally:
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
