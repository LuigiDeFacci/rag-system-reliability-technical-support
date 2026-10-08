param(
    [int]$MaxTrackedFileMB = 10
)

$ErrorActionPreference = "Stop"

$tracked = @(git ls-files)
if ($LASTEXITCODE -ne 0) { throw "Falha ao listar arquivos rastreados pelo Git." }

if (-not (Test-Path -LiteralPath "LICENSE" -PathType Leaf)) {
    throw "Arquivo LICENSE ausente."
}

$forbiddenExtensions = @(".tar.gz", ".parquet", ".npy", ".safetensors", ".joblib", ".docx", ".pdf")
$forbiddenNames = @(".env", ".env.local", ".env.production")
$textExtensions = @(".md", ".txt", ".yaml", ".yml", ".json", ".csv", ".ipynb", ".py", ".ps1", ".toml", ".cff", ".svg")
$violations = [System.Collections.Generic.List[string]]::new()
if ($tracked -notcontains "LICENSE") {
    $violations.Add("O arquivo LICENSE ainda não está rastreado pelo Git.")
}

foreach ($path in $tracked) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        $violations.Add("Arquivo rastreado ausente no disco: $path")
        continue
    }
    $item = Get-Item -LiteralPath $path
    $lowerPath = $path.ToLowerInvariant().Replace('\', '/')
    if ($forbiddenExtensions | Where-Object { $lowerPath.EndsWith($_) }) {
        $violations.Add("Extensão inadequada para esta publicação: $path")
    }
    if ($forbiddenNames -contains [System.IO.Path]::GetFileName($lowerPath)) {
        $violations.Add("Arquivo de ambiente rastreado: $path")
    }
    if ($lowerPath -match '(^|/)(referemcoas|rags -docs from course|old|data/(raw|interim|processed)|results/runs)/' -and
        -not $lowerPath.EndsWith('/.gitkeep')) {
        $violations.Add("Material local ou derivado rastreado: $path")
    }
    if ($item.Length -gt ($MaxTrackedFileMB * 1MB)) {
        $violations.Add("Arquivo acima de $MaxTrackedFileMB MB: $path ($([math]::Round($item.Length / 1MB, 2)) MB)")
    }

    if ($textExtensions -notcontains [System.IO.Path]::GetExtension($lowerPath)) { continue }
    $content = [System.IO.File]::ReadAllText($item.FullName)
    $patterns = @(
        '-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----',
        '\bsk-[A-Za-z0-9]{20,}\b',
        '\bAIza[0-9A-Za-z_-]{35}\b',
        '(?i)\b(?:api[_-]?key|access[_-]?token|password|secret)\s*[:=]\s*["'']?[A-Za-z0-9_./+=-]{8,}',
        ('(?i)(?:[A-Z]:\\Us' + 'ers\\[^\\\s"'']+|/Us' + 'ers/[^/\s"'']+|/ho' + 'me/[^/\s"'']+)')
    )
    if ($patterns | Where-Object { [regex]::IsMatch($content, $_) }) {
        $violations.Add("Possível segredo ou caminho pessoal no conteúdo: $path (revisar manualmente)")
    }
}

if ($violations.Count -gt 0) {
    $violations | ForEach-Object { [Console]::Error.WriteLine($_) }
    exit 1
}

Write-Host "Public-release check passed: $($tracked.Count) tracked paths inspected."
