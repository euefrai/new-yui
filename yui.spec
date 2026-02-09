# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec para gerar o executável da Yui (interface gráfica).
# Uso: pyinstaller yui.spec   (execute na pasta do projeto)
# Saída: dist/Yui.exe

import os

# Na execução do spec, __file__ pode não existir; usar diretório de trabalho (pasta do projeto).
ROOT = os.path.abspath(os.curdir)

a = Analysis(
    [os.path.join(ROOT, 'run_yui_gui.py')],
    pathex=[ROOT],
    binaries=[],
    datas=[],
    hiddenimports=[
        'yui_ai',
        'yui_ai.gui',
        'yui_ai.gui.app',
        'yui_ai.gui.main_window',
        'yui_ai.gui.chat_widget',
        'yui_ai.gui.input_bar',
        'yui_ai.gui.styles',
        'yui_ai.gui.yui_bridge',
        'yui_ai.memory',
        'yui_ai.memory.memory',
        'yui_ai.main',
        'yui_ai.actions.actions',
        'yui_ai.core.intent_parser',
        'yui_ai.core.decision_engine',
        'yui_ai.core.execution_engine',
        'yui_ai.core.file_resolver',
        'yui_ai.core.macro_engine',
        'yui_ai.core.teaching_engine',
        'yui_ai.core.ai_engine',
        'yui_ai.core.sequence_engine',
        'yui_ai.core.autonomy_engine',
        'yui_ai.system.app_launcher',
        'yui_ai.system.app_indexer',
        'yui_ai.permissions.permissions',
        'yui_ai.validation.validation_engine',
        'yui_ai.code_editor.code_generator',
        'yui_ai.code_editor.file_manager',
        'yui_ai.code_editor.patch_engine',
        'yui_ai.code_editor.planning_engine',
        'PySide6.QtWidgets',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'dotenv',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Yui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,   # Sem janela de console (só GUI)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
