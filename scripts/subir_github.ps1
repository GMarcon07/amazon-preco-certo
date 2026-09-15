[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Publicar no GitHub Actions (100% Automatico via Terminal)     " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Adicionar git e gh ao PATH temporario se necessario
$gitCmdPath = "$env:LOCALAPPDATA\Programs\MinGit\cmd"
$ghPath = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\GitHub.cli_Microsoft.Winget.Source_8wekyb3d8bbwe\bin"
$env:Path = "$env:Path;$gitCmdPath;$ghPath"

# 1. Verificar autenticacao no GitHub
Write-Host "[1/5] A verificar login no GitHub..." -ForegroundColor Yellow
$authStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Precisas de autorizar o GitHub CLI no teu navegador." -ForegroundColor Magenta
    Write-Host "Ira abrir uma janela no navegador para fazeres login com 1 clique..." -ForegroundColor Magenta
    gh auth login --web -h github.com -p https
}

# 2. Configurar Git local
Write-Host ""
Write-Host "[2/5] A preparar repositorio Git local..." -ForegroundColor Yellow

$baseDir = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $baseDir

if (-not (Test-Path ".git")) {
    git init
    git branch -M main
}

# Configurar autor se ainda nao estiver definido
$gitUser = git config user.name
if (-not $gitUser) {
    git config user.name "Gabriel"
    git config user.email "gabriel@local.com"
}

git add .
git commit -m "Monitor de Falhas de Preco Amazon Gaming" 2>$null

# 3. Criar repositorio no GitHub e enviar ficheiros
Write-Host ""
Write-Host "[3/5] A criar repositorio no GitHub e a enviar ficheiros..." -ForegroundColor Yellow

$repoName = "amazon-preco-certo"
# Tenta criar o repositorio publico
gh repo create $repoName --public --source=. --remote=origin --push 2>&1

# Se o repositorio ja existia, apenas faz push
if ($LASTEXITCODE -ne 0) {
    git push -u origin main
}

# 4. Configurar o segredo do Discord no GitHub
Write-Host ""
Write-Host "[4/5] A configurar DISCORD_WEBHOOK_URL nos segredos do GitHub..." -ForegroundColor Yellow

$envFile = Join-Path $baseDir ".env"
$webhookUrl = ""
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^DISCORD_WEBHOOK_URL=(.+)$") {
            $webhookUrl = $matches[1].Trim()
        }
    }
}

if ($webhookUrl) {
    $webhookUrl | gh secret set DISCORD_WEBHOOK_URL
    Write-Host "Segredo DISCORD_WEBHOOK_URL configurado com sucesso!" -ForegroundColor Green
} else {
    Write-Host "Aviso: Webhook nao encontrado no .env. Configure manualmente com 'gh secret set DISCORD_WEBHOOK_URL'." -ForegroundColor Yellow
}

# 5. Disparar a primeira execucao do monitor
Write-Host ""
Write-Host "[5/5] A disparar a primeira execucao no GitHub Actions..." -ForegroundColor Yellow
gh workflow run monitor.yml 2>$null

Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  SUCESSO! O teu robô esta agora a rodar na nuvem do GitHub!   " -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "O monitor ira correr sozinho a cada 30 minutos na nuvem (24/7)," -ForegroundColor Cyan
Write-Host "mesmo que o teu computador esteja 100% desligado." -ForegroundColor Cyan
Write-Host ""
Write-Host "Podes acompanhar os scans e logs no teu repositorio:" -ForegroundColor Gray
gh repo view --web
