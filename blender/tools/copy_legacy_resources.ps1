$ErrorActionPreference = 'Stop'
$projectRoot = 'D:\codex\blender'
$legacyRoot = 'C:\Users\littl\Documents\Codex\2026-11-05\z'
$mappings = @(
    @{ Source = "$legacyRoot\outputs\TeddyRoom_Study"; Target = "$projectRoot\scenes\TeddyRoom_Study" },
    @{ Source = "$legacyRoot\outputs\SakuraLane_Study"; Target = "$projectRoot\scenes\SakuraLane_Study" },
    @{ Source = "$legacyRoot\outputs\TeddyRoom_Study_完整学习包.zip"; Target = "$projectRoot\learning\packages\original\TeddyRoom_Study_完整学习包.zip" },
    @{ Source = "$legacyRoot\outputs\SakuraLane_Study_完整学习包.zip"; Target = "$projectRoot\learning\packages\original\SakuraLane_Study_完整学习包.zip" },
    @{ Source = "$legacyRoot\outputs\Blender_Agent_场景制作与视觉验收指南.md"; Target = "$projectRoot\learning\materials\Blender_Agent_场景制作与视觉验收指南.md" },
    @{ Source = "$legacyRoot\work\teddy_scene"; Target = "$projectRoot\archive\run_logs\teddy_scene" },
    @{ Source = "$legacyRoot\work\sakura_scene"; Target = "$projectRoot\archive\run_logs\sakura_scene" }
)
$records = [System.Collections.Generic.List[object]]::new()
foreach ($mapping in $mappings) {
    if (Test-Path -LiteralPath $mapping.Target) { throw "Destination already exists: $($mapping.Target)" }
    $sourceItem = Get-Item -LiteralPath $mapping.Source
    $parent = Split-Path -Parent $mapping.Target
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    Copy-Item -LiteralPath $mapping.Source -Destination $mapping.Target -Recurse
    $sourceFiles = if ($sourceItem.PSIsContainer) { @(Get-ChildItem -LiteralPath $mapping.Source -File -Recurse) } else { @($sourceItem) }
    foreach ($file in $sourceFiles) {
        $relative = if ($sourceItem.PSIsContainer) { $file.FullName.Substring($mapping.Source.Length).TrimStart('\') } else { '' }
        $targetFile = if ($relative) { Join-Path $mapping.Target $relative } else { $mapping.Target }
        $beforeHash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
        $targetHash = (Get-FileHash -LiteralPath $targetFile -Algorithm SHA256).Hash
        if ($beforeHash -ne $targetHash) { throw "Hash mismatch: $($file.FullName)" }
        $records.Add([pscustomobject]@{ source = $file.FullName; destination = $targetFile; bytes = $file.Length; original_sha256 = $beforeHash; copied_sha256 = $targetHash; copy_verified = $true; source_removed = $false })
    }
}
$manifest = [ordered]@{ created_at = (Get-Date -Format o); project_root = $projectRoot; legacy_root = $legacyRoot; status = 'copied_and_hash_verified_pending_source_cleanup'; records = @($records.ToArray()) }
New-Item -ItemType Directory -Force -Path "$projectRoot\docs" | Out-Null
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath "$projectRoot\docs\migration_manifest.json" -Encoding utf8
[pscustomobject]@{ verified_files = $records.Count; bytes = ($records | Measure-Object -Property bytes -Sum).Sum; destination = $projectRoot } | ConvertTo-Json
