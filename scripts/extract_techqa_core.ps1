[CmdletBinding()]
param(
    [string]$Archive = "data/raw/TechQA.tar.gz",
    [string]$Destination = "data/raw",
    [string]$ExpectedSha256 = "6b094ef9a69718f727ce8d7e15c4d961e51032cefaa952e0d6af9d176d7ba118"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$archivePath = [System.IO.Path]::GetFullPath((Join-Path $root $Archive))
$destinationPath = [System.IO.Path]::GetFullPath((Join-Path $root $Destination))
$actualHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()

if ($actualHash -ne $ExpectedSha256.ToLowerInvariant()) {
    throw "Refusing to extract an archive with an unexpected SHA-256."
}

$members = @(
    "TechQA/README.txt",
    "TechQA/CDLA-Permissive-v1.0.pdf",
    "TechQA/evaluation.py",
    "TechQA/training_and_dev/training_Q_A.json",
    "TechQA/training_and_dev/dev_Q_A.json",
    "TechQA/training_and_dev/training_Q_A.txt",
    "TechQA/training_and_dev/training_dev_technotes.json",
    "TechQA/training_and_dev/training_dev_technotes.sections.json",
    "TechQA/validation/validation_questions.json",
    "TechQA/validation/validation_reference.json",
    "TechQA/validation/validation_example_output.json",
    "TechQA/validation/validation_technotes.json"
)

& tar -xzf $archivePath -C $destinationPath @members
if ($LASTEXITCODE -ne 0) {
    throw "tar failed with exit code $LASTEXITCODE"
}

Write-Output "Core TechQA files extracted to $destinationPath"
