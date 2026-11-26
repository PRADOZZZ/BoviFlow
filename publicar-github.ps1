$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
function Run([string]$exe, [string[]]$argv) {
    & $exe @argv
    if ($LASTEXITCODE -ne 0) { throw "Falha: $exe (codigo $LASTEXITCODE). Confira a mensagem acima." }
}
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User') + ';' + $env:Path
    foreach ($p in @("$env:ProgramFiles\Git\cmd", "$env:ProgramFiles\GitHub CLI", "$env:LOCALAPPDATA\Programs\GitHub CLI")) { if (Test-Path $p) { $env:Path += ';' + $p } }
}
try {
    $manifest = Get-Content -Raw -LiteralPath (Join-Path $root 'arquivos-publicacao.json') | ConvertFrom-Json
    foreach ($item in $manifest.files) {
        $p = Join-Path $root $item.path
        if (-not (Test-Path -LiteralPath $p -PathType Leaf)) { throw "Arquivo ausente: $($item.path). Extraia o ZIP inteiro." }
        if ((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -ne $item.sha256) { throw "Arquivo alterado: $($item.path). Extraia o ZIP original." }
    }
    foreach ($p in @('api/session.py','public/index.html','public/static/app.js','public/static/style.css','public/static/bovinus.png','public/static/plant.png','docs/openapi.json','vercel.json')) { if (-not (Test-Path -LiteralPath (Join-Path $root $p))) { throw "Arquivo essencial ausente: $p" } }
    Write-Host "Integridade OK: $($manifest.files.Count) arquivos." -ForegroundColor Green
    Refresh-Path
    foreach ($dep in @(@('git','Git.Git'),@('gh','GitHub.cli'))) {
        if (-not (Get-Command $dep[0] -ErrorAction SilentlyContinue)) {
            if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw "Instale $($dep[0]) por https://git-scm.com/download/win ou https://cli.github.com/ e execute novamente." }
            if ((Read-Host "Instalar $($dep[0]) pelo winget? Digite SIM") -ne 'SIM') { return }
            Run 'winget' @('install','--id',$dep[1],'-e','--accept-source-agreements','--accept-package-agreements')
            Refresh-Path
            if (-not (Get-Command $dep[0] -ErrorAction SilentlyContinue)) { throw 'Instalacao concluida; feche esta janela e execute novamente.' }
        }
    }
    & gh auth status --hostname github.com
    if ($LASTEXITCODE -ne 0) { Run 'gh' @('auth','login','--hostname','github.com','--git-protocol','https','--web') }
    $owner = (& gh api user --jq '.login').Trim()
    if ($LASTEXITCODE -ne 0 -or $owner -ne 'PRADOZZZ') { throw "Conta incorreta: $owner. Autentique a conta PRADOZZZ antes de continuar." }
    Run 'gh' @('auth','setup-git')
    $repo = "$owner/BoviFlow"
    Write-Host "Destino: $repo. Se nao existir, sera criado como PRIVADO. Historico existente sera preservado." -ForegroundColor Cyan
    if ((Read-Host 'Confirma criar/enviar o projeto completo? Digite SIM') -ne 'SIM') { return }
    $work = Join-Path ([System.IO.Path]::GetTempPath()) ('BoviFlow-publicacao-' + [guid]::NewGuid().ToString('N'))
    $existing = & gh repo view $repo --json name,defaultBranchRef --jq '.defaultBranchRef.name' 2>$null
    $exists = $LASTEXITCODE -eq 0
    if ($exists) {
        Run 'git' @('clone',"https://github.com/$repo.git",$work)
    } else {
        New-Item -ItemType Directory -Path $work | Out-Null
        Run 'git' @('-C',$work,'init','-b','main')
    }
    Push-Location $work
    try {
        foreach ($item in $manifest.files) {
            $dst = Join-Path $work $item.path
            $parent = Split-Path -Parent $dst
            if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
            Copy-Item -LiteralPath (Join-Path $root $item.path) -Destination $dst -Force
            Run 'git' @('add','--',$item.path)
        }
        Copy-Item -LiteralPath (Join-Path $root 'arquivos-publicacao.json') -Destination $work -Force
        Run 'git' @('add','--','arquivos-publicacao.json')
        foreach ($p in @('api/session.py','public/index.html','public/static/app.js','docs/openapi.json')) { Run 'git' @('ls-files','--error-unmatch',$p) }
        & git diff --cached --quiet
        $diff = $LASTEXITCODE
        if ($diff -eq 1) {
            $uid = (& gh api user --jq '.id').Trim()
            if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel confirmar o usuario GitHub.' }
            Run 'git' @('-c',"user.name=$owner",'-c',"user.email=$uid+$owner@users.noreply.github.com",'commit','-m','BoviFlow: entrega completa e validada para Vercel')
        } elseif ($diff -ne 0) { throw 'Falha ao verificar alteracoes.' }
        if ($exists) { Run 'git' @('push','origin','HEAD') } else { Run 'gh' @('repo','create',$repo,'--private','--source=.','--remote=origin','--push') }
        $branch = (& git branch --show-current).Trim()
        $local = (& git rev-parse HEAD).Trim()
        $remote = (& gh api "repos/$repo/commits/$branch" --jq '.sha').Trim()
        if ($LASTEXITCODE -ne 0 -or $local -ne $remote) { throw 'Nao foi possivel confirmar o commit remoto.' }
        foreach ($item in $manifest.files) {
            $remoteHash = (& git hash-object -- (Join-Path $root $item.path)).Trim()
            $treeHash = (& git rev-parse "HEAD:$($item.path)").Trim()
            if ($LASTEXITCODE -ne 0 -or $remoteHash -ne $treeHash) { throw "Arquivo nao confirmado no commit: $($item.path)" }
        }
        Write-Host "PUBLICADO NO GITHUB: https://github.com/$repo (commit $local)" -ForegroundColor Green
        Write-Host 'Importe o repositorio na Vercel. Framework Other, raiz ./, output public.'
        Start-Process "https://github.com/$repo"
        Start-Process 'https://vercel.com/new'
    } finally { Pop-Location }
} catch { Write-Host $_.Exception.Message -ForegroundColor Red; if ($work) { Write-Host "Copia local (se criada): $work" }; exit 1 }
