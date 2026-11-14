# One-time source cleanup. Requires explicit filesystem write access to legacy targets.
$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot)).TrimEnd('\')
$legacyRoot = 'C:\Users\littl\Documents\Codex\2026-11-05\z'
$manifestPath = Join-Path $projectRoot 'docs\migration_manifest.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$projectCheck = Get-Content -LiteralPath (Join-Path $projectRoot 'docs\project_verification.json') -Raw | ConvertFrom-Json
if (-not $projectCheck.passed) { throw 'Project verification has not passed.' }
$targets = @(
    "$legacyRoot\outputs\TeddyRoom_Study",
    "$legacyRoot\outputs\SakuraLane_Study",
    "$legacyRoot\outputs\TeddyRoom_Study_完整学习包.zip",
    "$legacyRoot\outputs\SakuraLane_Study_完整学习包.zip",
    "$legacyRoot\outputs\Blender_Agent_场景制作与视觉验收指南.md",
    "$legacyRoot\work\teddy_scene",
    "$legacyRoot\work\sakura_scene"
)
# Inspect every source and destination before deleting anything.
foreach ($record in $manifest.records) {
    $destination = [System.IO.Path]::GetFullPath($record.destination)
    if (-not $destination.StartsWith($projectRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)) { throw "Destination outside project: $destination" }
    if (-not $record.copy_verified -or $record.copied_sha256 -ne $record.original_sha256) { throw 'Original copy was not verified.' }
    if ((Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash -ne $record.final_sha256) { throw "Destination changed after final verification: $destination" }
    if (-not (Test-Path -LiteralPath $record.source -PathType Leaf)) { throw "Source no longer present; inspect before retrying: $($record.source)" }
    if ((Get-FileHash -LiteralPath $record.source -Algorithm SHA256).Hash -ne $record.original_sha256) { throw "Source changed since copy; do not remove: $($record.source)" }
}
foreach ($target in $targets) {
    $resolved = (Resolve-Path -LiteralPath $target).Path.TrimEnd('\')
    $expected = [System.IO.Path]::GetFullPath($target).TrimEnd('\')
    if (-not $resolved.Equals($expected, [System.StringComparison]::OrdinalIgnoreCase)) { throw "Unexpected resolved cleanup target: $resolved" }
    if ($resolved -notin $targets -or $resolved -eq $legacyRoot) { throw "Cleanup target not explicitly allowed: $resolved" }
    $item = Get-Item -LiteralPath $resolved
    $allItems = @($item)
    if ($item.PSIsContainer) { $allItems += @(Get-ChildItem -LiteralPath $resolved -Recurse -Force) }
    if (@($allItems | Where-Object { $_.Attributes -band [System.IO.FileAttributes]::ReparsePoint }).Count) { throw "Reparse point in cleanup target: $resolved" }
    $files = @($allItems | Where-Object { -not $_.PSIsContainer } | ForEach-Object FullName)
    $expectedSources = @($manifest.records | Where-Object { $_.source -eq $resolved -or $_.source.StartsWith($resolved + '\', [System.StringComparison]::OrdinalIgnoreCase) } | ForEach-Object source)
    if ($files.Count -ne $expectedSources.Count -or @(Compare-Object -ReferenceObject $expectedSources -DifferenceObject $files).Count) { throw "Source tree changed or contains unrecorded files: $resolved" }
}
try {
    foreach ($target in $targets) {
        # These exact absolute targets were resolved and checked above.
        Remove-Item -LiteralPath $target -Recurse -Force
    }
} finally {
    foreach ($record in $manifest.records) { $record.source_removed = -not (Test-Path -LiteralPath $record.source) }
    $remaining = @($manifest.records | Where-Object { -not $_.source_removed }).Count
    $manifest.status = if ($remaining -eq 0) { 'move_complete' } else { 'source_cleanup_incomplete' }
    $manifest | Add-Member -NotePropertyName cleanup_checked_at -NotePropertyValue (Get-Date -Format o) -Force
    $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding utf8
}
if ($manifest.status -ne 'move_complete') { throw 'Some original sources remain. See migration manifest.' }
Write-Output "Move complete: $($manifest.records.Count) verified original files; seven explicit source targets removed."
