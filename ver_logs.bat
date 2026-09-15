@echo off
chcp 65001 > nul
echo ================================================================
echo   Logs em Tempo Real — Monitor Amazon (Ctrl + C para sair)
echo ================================================================
echo.

powershell -NoProfile -Command "if (Test-Path 'data\monitor.log') { Get-Content -Path 'data\monitor.log' -Wait -Tail 35 } else { Write-Host 'Ficheiro de logs ainda não existe. Inicie o monitor primeiro.' }"
