$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$projectRoot = Split-Path -Parent $PSScriptRoot
$packageDir = Join-Path $projectRoot 'learning\packages'
New-Item -ItemType Directory -Force -Path $packageDir | Out-Null
$records = @()
foreach ($caseName in @('TeddyRoom_Study', 'SakuraLane_Study', 'TeddyRoom_Rebuild_20261110')) {
    $caseRoot = Join-Path $projectRoot "scenes\$caseName"
    $packagePath = Join-Path $packageDir ($caseName + '_完整学习包.zip')
    $temporaryPath = $packagePath + '.building'
    if (Test-Path -LiteralPath $temporaryPath) { throw "Previous incomplete package exists: $temporaryPath" }
    $files = @(Get-ChildItem -LiteralPath $caseRoot -Recurse -File | Where-Object { $_.Name -notmatch '\.blend\d+$' })
    $zip = [System.IO.Compression.ZipFile]::Open($temporaryPath, [System.IO.Compression.ZipArchiveMode]::Create)
    try {
        foreach ($file in $files) {
            $relative = $file.FullName.Substring($caseRoot.Length).TrimStart('\').Replace('\', '/')
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $file.FullName, "$caseName/$relative", [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
        }
    } finally { $zip.Dispose() }
    Move-Item -LiteralPath $temporaryPath -Destination $packagePath -Force
    $records += [pscustomobject]@{
        scene = $caseName; package = "learning/packages/$caseName`_完整学习包.zip"
        file_count = $files.Count; bytes = (Get-Item -LiteralPath $packagePath).Length
        sha256 = (Get-FileHash -LiteralPath $packagePath -Algorithm SHA256).Hash
        excluded = @('*.blend1 and other numbered .blend backups')
    }
}
[ordered]@{ generated_at = (Get-Date -Format o); packages = $records } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $packageDir 'package_manifest.json') -Encoding utf8
$records | Select-Object scene, file_count, bytes | Format-Table

