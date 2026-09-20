@echo off
chcp 65001 >nul
title Sidekick - Copiloto Gamer Universal

if exist "dist\Sidekick.exe" (
    start "" "dist\Sidekick.exe"
) else if exist "Sidekick.exe" (
    start "" "Sidekick.exe"
) else (
    echo [Sidekick] Executavel nao encontrado em dist\. Iniciando via Python GUI...
    python run_gui.py
)
exit
