@echo off
chcp 65001 > nul
echo ================================================================
echo   Parar Monitor de Preços em Segundo Plano
echo ================================================================
echo.

echo A procurar processos ativos do monitor...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*run.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host ('Encerrado processo PID ' + $_.ProcessId) }"

echo.
echo ✅ Monitor encerrado com sucesso.
echo.
pause
