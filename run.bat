@echo off
setlocal enabledelayedexpansion
title Fotus - Analise de Fabricantes
echo ============================================
echo  Fotus Distribuidora Solar
echo  Dashboard de Analise de Fabricantes
echo ============================================
echo.

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado nesta maquina.
    echo Instale o Python 3.10 ou superior em https://www.python.org/downloads/
    echo IMPORTANTE: na instalacao, marque a opcao "Add Python to PATH".
    pause
    exit /b 1
)

REM ── Configuracao da chave de API (.env) ──────────────────────────────────
if not exist ".env" (
    echo [SETUP] Primeira execucao: preparando arquivo de configuracao...
    copy ".env.example" ".env" >nul
    echo.
    echo ============================================
    echo  ACAO NECESSARIA
    echo ============================================
    echo  Uma janela do Bloco de Notas vai abrir com o arquivo .env
    echo  Substitua "cole_aqui_sua_chave_da_anthropic" pela SUA chave
    echo  da Anthropic (comeca com "sk-ant-..."), salve o arquivo (Ctrl+S)
    echo  e feche o Bloco de Notas. Depois, rode este run.bat novamente.
    echo ============================================
    pause
    notepad ".env"
    exit /b 0
)

findstr /C:"cole_aqui_sua_chave_da_anthropic" ".env" >nul
if %errorlevel% equ 0 (
    echo [ERRO] O arquivo .env ainda tem o valor de exemplo, nao a sua chave real.
    echo Abrindo o Bloco de Notas para voce colar a chave da Anthropic...
    pause
    notepad ".env"
    exit /b 1
)

REM ── Ambiente virtual isolado (evita conflito com outros Python no PC) ────
if not exist ".venv" (
    echo [1/3] Criando ambiente virtual Python...
    python -m venv .venv
)

echo [2/3] Instalando/atualizando dependencias...
".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet --disable-pip-version-check

echo [3/3] Iniciando servidor...
echo.
echo  Acesse: http://localhost:5000
echo  Pressione CTRL+C nesta janela para encerrar
echo.
".venv\Scripts\python.exe" app.py
pause
