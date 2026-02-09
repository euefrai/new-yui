@echo off
REM Gera o executável Yui.exe para distribuição em outros PCs.
REM Requer: Python com PyInstaller e dependências da Yui instaladas.

cd /d "%~dp0"

echo Verificando PyInstaller...
python -c "import PyInstaller" 2>nul || (
    echo Instalando PyInstaller...
    pip install pyinstaller
)

echo Instalando dependencias da Yui...
pip install -q PySide6 python-dotenv openai

echo.
echo Gerando executavel (pode levar alguns minutos)...
pyinstaller --noconfirm yui.spec

if %ERRORLEVEL% equ 0 (
    echo.
    echo Pronto. Executavel em: dist\Yui.exe
    echo Copie dist\Yui.exe para outro computador e execute. Nao precisa instalar Python.
) else (
    echo Erro ao gerar o executavel.
    exit /b 1
)
