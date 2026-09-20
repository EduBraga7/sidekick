@echo off
chcp 65001 >nul
title Sidekick — Copiloto Gamer Universal

echo ============================================================
echo   🎮 SIDEKICK — SEU COPILOTO GAMER UNIVERSAL
echo ============================================================
echo.

:: 1. Se já existir o executável compilado, executa direto
if exist "dist\Sidekick.exe" (
    echo [Sidekick] Iniciando executavel portatil...
    start "" "dist\Sidekick.exe"
    exit
)
if exist "Sidekick.exe" (
    echo [Sidekick] Iniciando executavel...
    start "" "Sidekick.exe"
    exit
)

:: 2. Verifica se o Python esta instalado
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado no seu computador!
    echo.
    echo Por favor, instale o Python 3.10 ou superior:
    echo https://www.python.org/downloads/
    echo.
    echo ATENCAO: Na instalacao do Python, MARQUE a opcao:
    echo "[x] Add python.exe to PATH"
    echo.
    pause
    exit
)

:: 3. Se for a primeira execucao, cria o ambiente virtual automaticamente
if not exist "venv" (
    echo [Sidekick] Primeira execucao detectada!
    echo [Sidekick] Configurando ambiente virtual (isso so acontece 1 vez)...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERRO] Falha ao criar ambiente virtual venv.
        pause
        exit
    )
    echo [Sidekick] Instalando dependencias do projeto...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERRO] Falha ao instalar dependencias do requirements.txt.
        pause
        exit
    )
    echo [OK] Ambiente configurado com sucesso!
    echo.
) else (
    call venv\Scripts\activate.bat
)

:: 4. Cria .env se nao existir
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo [AVISO] Arquivo .env criado a partir do .env.example.
        echo         Lembre-se de abrir o .env e colocar sua chave do Groq!
        echo.
    )
)

:: 5. Cria config.json se nao existir
if not exist "config.json" (
    if exist "config.safe.example.json" (
        copy config.safe.example.json config.json >nul
    )
)

:: 6. Inicia a interface grafica do Sidekick
echo [Sidekick] Abrindo interface grafica...
python main.py

if %errorlevel% neq 0 (
    echo.
    echo [AVISO] O Sidekick foi encerrado.
    pause
)
exit
