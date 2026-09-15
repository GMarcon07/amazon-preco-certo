[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Parar Monitor de Precos em Segundo Plano                     " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*run.py*" }

if ($procs) {
    foreach ($p in $procs) {
        Write-Host "A terminar processo PID $($p.ProcessId)..." -ForegroundColor Yellow
        Stop-Process -Id $p.ProcessId -Force
    }
    Write-Host ""
    Write-Host "[SUCESSO] Todos os processos do monitor foram encerrados." -ForegroundColor Green
} else {
    Write-Host "[INFO] O monitor nao esta atualmente em execucao." -ForegroundColor Yellow
}
