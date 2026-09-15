[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Instalacao do Arranque Automatico 24/7 (Amazon Preco Certo)  " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

$baseDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$vbsFile = Join-Path $baseDir "iniciar_segundo_plano.vbs"
$startupFolder = [System.Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startupFolder "Amazon_Preco_Certo.lnk"

Write-Host "A criar atalho na pasta de arranque do Windows ($startupFolder)..." -ForegroundColor Yellow

$wshShell = New-Object -ComObject WScript.Shell
$shortcut = $wshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "wscript.exe"
$shortcut.Arguments = "`"$vbsFile`""
$shortcut.WorkingDirectory = "$baseDir"
$shortcut.WindowStyle = 7 # Minimized / Hidden
$shortcut.Description = "Monitor de Falhas de Preco Amazon Gaming"
$shortcut.Save()

if (Test-Path $shortcutPath) {
    Write-Host ""
    Write-Host "[CONCLUIDO COM SUCESSO]" -ForegroundColor Green
    Write-Host "O monitor foi registado para arrancar de forma 100% invisivel sempre que ligares o PC!" -ForegroundColor Green
    Write-Host "Atalho criado em: $shortcutPath" -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "[ERRO] Nao foi possivel criar o atalho." -ForegroundColor Red
}
