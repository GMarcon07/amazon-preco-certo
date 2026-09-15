[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Remocao do Arranque Automatico (Amazon Preco Certo)           " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

$startupFolder = [System.Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startupFolder "Amazon_Preco_Certo.lnk"

if (Test-Path $shortcutPath) {
    Remove-Item -Path $shortcutPath -Force
    Write-Host "[REMOVIDO COM SUCESSO]" -ForegroundColor Green
    Write-Host "O monitor ja nao vai arrancar automaticamente ao ligar o PC." -ForegroundColor Green
} else {
    Write-Host "[INFO] Nenhum atalho foi encontrado na pasta de arranque." -ForegroundColor Yellow
}
