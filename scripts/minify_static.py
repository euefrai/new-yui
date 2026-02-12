#!/usr/bin/env python3
"""
Minifica CSS e JS para produção (Zeabur).
Gera static/*.min.js e static/*.min.css.
Uso: python scripts/minify_static.py
"""
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
STATIC = BASE / "static"

JS_FILES = ["app.js", "chat.js", "editor.js", "workspace-project.js", "workspace-terminal.js"]
CSS_FILES = ["style.css"]


def minify_js(text: str) -> str:
    """Minificação básica de JS (remove comentários e espaços extras)."""
    text = re.sub(r"//[^\n]*", "", text)
    text = re.sub(r"/\*[\s\S]*?\*/", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def minify_css(text: str) -> str:
    """Minificação básica de CSS."""
    text = re.sub(r"/\*[\s\S]*?\*/", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def main():
    for name in JS_FILES:
        src = STATIC / name
        dst = STATIC / name.replace(".js", ".min.js")
        if src.exists():
            out = minify_js(src.read_text(encoding="utf-8"))
            dst.write_text(out, encoding="utf-8")
            print(f"  {name} -> {dst.name}")
    for name in CSS_FILES:
        src = STATIC / name
        dst = STATIC / name.replace(".css", ".min.css")
        if src.exists():
            out = minify_css(src.read_text(encoding="utf-8"))
            dst.write_text(out, encoding="utf-8")
            print(f"  {name} -> {dst.name}")
    print("Minificação concluída. Use USE_MINIFIED_STATIC=true no Zeabur.")


if __name__ == "__main__":
    main()
    sys.exit(0)
