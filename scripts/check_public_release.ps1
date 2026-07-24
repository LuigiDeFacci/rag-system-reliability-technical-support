param(
    [int]$MaxTrackedFileMB = 10
)

$ErrorActionPreference = "Stop"

$tracked = git ls-files
$forbiddenExtensions = @(".tar.gz", ".parquet", ".npy", ".safetensors", ".joblib", ".docx", ".pdf")
$violations = @()

foreach ($path in $tracked) {
    if (-not (Test-Path -LiteralPath $path)) { continue }
    $item = Get-Item -LiteralPath $path
    $extensionViolation = $forbiddenExtensions | Where-Object { $path.ToLowerInvariant().EndsWith($_) }
    if ($extensionViolation) {
        $violations += "Arquivo com extensão não publicada: $path"
    }
    if ($item.Length -gt ($MaxTrackedFileMB * 1MB)) {
        $violations += "Arquivo acima do limite de $MaxTrackedFileMB MB: $path ($([math]::Round($item.Length / 1MB, 2)) MB)"
    }
}

$trackedText = $tracked -join "`n"
if ($trackedText -match "(?i)(sk-[A-Za-z0-9]|AIza|BEGIN PRIVATE KEY|api[_-]?key|password\s*=)") {
    $violations += "Possível segredo encontrado na lista de arquivos rastreados. Faça uma busca manual."
}

if ($violations.Count -gt 0) {
    $violations | ForEach-Object { Write-Error $_ }
    exit 1
}

Write-Host "Public-release check passed: $($tracked.Count) tracked paths inspected."
