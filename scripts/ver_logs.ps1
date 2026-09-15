[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Logs em Tempo Real — Monitor Amazon (Ctrl + C para sair)      " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

$baseDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$logPath = Join-Path $baseDir "data\monitor.log"

if (Test-Path $logPath) {
    Get-Content -Path $logPath -Wait -Tail 30
} else {
    Write-Host "[INFO] Ficheiro de logs data\monitor.log ainda nao existe." -ForegroundColor Yellow
    Write-Host "Inicie o monitor uma vez para gerar os primeiros logs."
}
