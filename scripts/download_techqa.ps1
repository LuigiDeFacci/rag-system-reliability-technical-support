[CmdletBinding()]
param(
    [string]$Url = "https://huggingface.co/datasets/PrimeQA/TechQA/resolve/main/TechQA.tar.gz?download=true",
    [string]$Output = "data/raw/TechQA.tar.gz",
    [long]$ExpectedBytes = 2959973525,
    [string]$ExpectedSha256 = "6b094ef9a69718f727ce8d7e15c4d961e51032cefaa952e0d6af9d176d7ba118"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$outputPath = [System.IO.Path]::GetFullPath((Join-Path $root $Output))
$outputDirectory = Split-Path -Parent $outputPath

if (-not (Test-Path -LiteralPath $outputDirectory)) {
    New-Item -ItemType Directory -Path $outputDirectory | Out-Null
}

$existingBytes = if (Test-Path -LiteralPath $outputPath) {
    (Get-Item -LiteralPath $outputPath).Length
} else {
    0L
}

if ($existingBytes -gt $ExpectedBytes) {
    throw "Existing file is larger than the expected archive."
}

if ($existingBytes -lt $ExpectedBytes) {
    Write-Output "Resuming download at $existingBytes of $ExpectedBytes bytes."
    & curl.exe `
        --ssl-no-revoke `
        --location `
        --fail `
        --retry 10 `
        --retry-delay 5 `
        --continue-at - `
        --output $outputPath `
        $Url
    if ($LASTEXITCODE -ne 0) {
        throw "curl failed with exit code $LASTEXITCODE"
    }
}

$actualBytes = (Get-Item -LiteralPath $outputPath).Length
if ($actualBytes -ne $ExpectedBytes) {
    throw "Archive size mismatch: expected $ExpectedBytes, got $actualBytes."
}

$actualHash = (Get-FileHash -LiteralPath $outputPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualHash -ne $ExpectedSha256.ToLowerInvariant()) {
    throw "SHA-256 mismatch: expected $ExpectedSha256, got $actualHash."
}

Write-Output "Download verified: $outputPath"
Write-Output "SHA256=$actualHash"

