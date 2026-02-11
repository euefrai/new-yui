#!/usr/bin/env python3
"""
Yui — Analisador técnico de projetos.

Entrypoint principal: análise de código via CLI.
Uso: yui analyze <caminho_do_projeto>

  python cli.py analyze ./projeto
  python -m yui_ai analyze ./projeto
"""

import argparse
import os
import sys

# Garante que a raiz do projeto está no path
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def cmd_analyze(path: str) -> int:
    """Executa análise do projeto em path. Retorna 0 em sucesso, 1 em erro."""
    from yui_ai.analyzer.report_builder import run_analysis

    resolved = os.path.abspath(path)
    if not os.path.isdir(resolved):
        print(f"Erro: diretório não encontrado: {resolved}", file=sys.stderr)
        return 1

    ok, data, err = run_analysis(resolved)
    if not ok:
        print(f"Erro na análise: {err}", file=sys.stderr)
        return 1

    print(data["texto_formatado"])
    return 0


def cmd_map(path: str) -> int:
    """Gera .yui_map.json com estrutura e dependências do projeto."""
    from core.project_mapper import generate_yui_map
    from pathlib import Path
    try:
        from config import settings
        default_root = str(Path(settings.SANDBOX_DIR).resolve())
    except Exception:
        default_root = "."
    root = Path(path or default_root).resolve()
    if not root.is_dir():
        print(f"Erro: diretório não encontrado: {root}", file=sys.stderr)
        return 1
    result = generate_yui_map(root)
    if result.get("ok"):
        print(f"✓ .yui_map.json gerado em {result.get('path', '')}")
        print(f"  Arquivos: {result.get('stats', {}).get('total_files', 0)}")
        return 0
    print(f"Erro: {result.get('error', 'desconhecido')}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="yui",
        description="Yui — Analisador técnico de projetos (somente leitura).",
    )
    subparsers = parser.add_subparsers(dest="command", help="Comandos")

    analyze_parser = subparsers.add_parser("analyze", help="Analisa um projeto (estrutura, dependências, riscos).")
    analyze_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Caminho da raiz do projeto (default: diretório atual)",
    )

    map_parser = subparsers.add_parser("map", help="Gera .yui_map.json (estrutura e dependências).")
    map_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Caminho da raiz (default: sandbox)",
    )

    args = parser.parse_args()

    if args.command == "analyze":
        return cmd_analyze(args.path)
    if args.command == "map":
        return cmd_map(args.path)
    if args.command is None:
        parser.print_help()
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
