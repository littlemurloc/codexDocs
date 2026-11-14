$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$projectRoot = Split-Path -Parent $PSScriptRoot
$reportPath = Join-Path $projectRoot 'docs\project_verification.json'
$migrationPath = Join-Path $projectRoot 'docs\migration_manifest.json'
$migration = Get-Content -LiteralPath $migrationPath -Raw | ConvertFrom-Json
if ($migration.status -eq 'move_complete') {
    foreach ($record in $migration.records) {
        if (-not $record.source_removed -or (Test-Path -LiteralPath $record.source)) { throw "Completed move still has legacy source: $($record.source)" }
    }
}
$editedSources = @('scenes/TeddyRoom_Study/README.md')
foreach ($record in $migration.records) {
    if (-not (Test-Path -LiteralPath $record.destination -PathType Leaf)) { throw "Missing migrated file: $($record.destination)" }
    $hash = (Get-FileHash -LiteralPath $record.destination -Algorithm SHA256).Hash
    $relative = $record.destination.Substring($projectRoot.Length).TrimStart('\').Replace('\', '/')
    if ($hash -ne $record.original_sha256 -and $relative -notin $editedSources) { throw "Unexpected post-copy change: $relative" }
    $record | Add-Member -NotePropertyName final_sha256 -NotePropertyValue $hash -Force
    $record | Add-Member -NotePropertyName edited_after_copy -NotePropertyValue ($hash -ne $record.original_sha256) -Force
}
$migration | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $migrationPath -Encoding utf8
$required = @('AGENTS.md','README.md','docs/PIPELINE.md','docs/CASE_LESSONS.md','docs/MIGRATION.md','templates/scene_brief.md','templates/work_state.md','templates/visual_review.md')
foreach ($path in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $projectRoot $path) -PathType Leaf)) { throw "Missing project file: $path" }
}
$packageManifest = Get-Content -LiteralPath (Join-Path $projectRoot 'learning\packages\package_manifest.json') -Raw | ConvertFrom-Json
$caseReports = @()
foreach ($caseName in @('TeddyRoom_Study','SakuraLane_Study','TeddyRoom_Rebuild_20261110')) {
    $caseRoot = Join-Path $projectRoot "scenes\$caseName"
    $mainFile = if ($caseName -eq 'TeddyRoom_Study') { 'scene.blend' } else { 'scene_cycles.blend' }
    foreach ($name in @('reference.png','README.md','index.html','scene_spec.json','cameras.json','validation.json','renders/05_final.png','renders/07_reopen_check.png',$mainFile,'scene_realtime.blend')) {
        if (-not (Test-Path -LiteralPath (Join-Path $caseRoot $name) -PathType Leaf)) { throw "Missing case file: $caseName/$name" }
    }
    $views = @(Get-ChildItem -LiteralPath (Join-Path $caseRoot 'renders') -Filter 'view_*.png' -File)
    if ($views.Count -ne 8) { throw "Expected eight views: $caseName" }
    $validation = Get-Content -LiteralPath (Join-Path $caseRoot 'validation.json') -Raw | ConvertFrom-Json
    if (@($validation.missing_external_images | Where-Object { $_ }).Count -or @($validation.external_missing | Where-Object { $_ }).Count) { throw "Historical validation reported missing images: $caseName" }
    $package = @($packageManifest.packages | Where-Object scene -eq $caseName)[0]
    $packagePath = Join-Path $projectRoot $package.package
    if ((Get-FileHash -LiteralPath $packagePath -Algorithm SHA256).Hash -ne $package.sha256) { throw "Package checksum mismatch: $caseName" }
    $zip = [System.IO.Compression.ZipFile]::OpenRead($packagePath)
    $entryCount = 0
    try {
        $expectedFiles = @(Get-ChildItem -LiteralPath $caseRoot -Recurse -File | Where-Object { $_.Name -notmatch '\.blend\d+$' })
        if ($zip.Entries.Count -ne $expectedFiles.Count) { throw "ZIP entry count mismatch: $caseName" }
        foreach ($file in $expectedFiles) {
            $relative = $file.FullName.Substring($caseRoot.Length).TrimStart('\').Replace('\', '/')
            $entry = $zip.GetEntry("$caseName/$relative")
            if (-not $entry) { throw "Missing ZIP entry: $caseName/$relative" }
            $stream = $entry.Open(); $sha = [System.Security.Cryptography.SHA256]::Create()
            try { $hash = [System.BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-', '') } finally { $stream.Dispose(); $sha.Dispose() }
            if ($hash -ne (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash) { throw "ZIP content mismatch: $caseName/$relative" }
            $entryCount++
        }
    } finally { $zip.Dispose() }
    $caseReports += [pscustomobject]@{ scene = $caseName; views = $views.Count; package_files_hash_verified = $entryCount; main_and_realtime_included = $true }
}
# Check local Markdown links and HTML image/link references without accessing the network.
$linkCount = 0
$textFiles = @(Get-ChildItem -LiteralPath $projectRoot -Recurse -File | Where-Object { $_.Extension -in @('.md','.html') -and $_.FullName -notlike '*\archive\*' })
foreach ($file in $textFiles) {
    $content = Get-Content -LiteralPath $file.FullName -Raw
    $matches = if ($file.Extension -eq '.html') { [regex]::Matches($content, '(?:src|href)=["'']([^"'']+)["'']') } else { [regex]::Matches($content, '\]\(([^)]+)\)') }
    foreach ($match in $matches) {
        $link = $match.Groups[1].Value.Trim('<','>')
        if ($link -match '^(?:[a-zA-Z]+:|#|//)' -or $link -match '[{}<>]') { continue }
        $link = [System.Uri]::UnescapeDataString(($link -split '[#?]')[0])
        if (-not $link) { continue }
        $resolved = Join-Path $file.DirectoryName $link
        # This invocation creates its own report only after every other check passes.
        if ([System.IO.Path]::GetFullPath($resolved) -ne $reportPath -and -not (Test-Path -LiteralPath $resolved)) { throw "Broken local link in $($file.FullName): $link" }
        $linkCount++
    }
}
$relocation = @()
foreach ($stem in @('teddy_cycles','teddy_realtime','sakura_cycles','sakura_realtime')) {
    $path = Join-Path $projectRoot "docs\relocation_checks\$stem.json"
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing relocation report: $stem" }
    $check = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
    if (-not $check.passed -or @($check.missing_dependencies).Count) { throw "Relocation failed: $stem" }
    if ($stem.EndsWith('cycles') -and (-not $check.rendered -or -not (Test-Path -LiteralPath $check.rendered))) { throw "Missing relocated render: $stem" }
    $relocation += $stem
}
$report = [ordered]@{
    checked_at = (Get-Date -Format o); passed = $true
    migrated_original_files = $migration.records.Count
    migration_status = $migration.status
    original_sources_removed = @($migration.records | Where-Object source_removed).Count
    original_bytes = ($migration.records | Measure-Object -Property bytes -Sum).Sum
    expected_document_edits = @($migration.records | Where-Object edited_after_copy | ForEach-Object destination)
    local_links_checked = $linkCount; cases = $caseReports; relocated_engineering_checks = $relocation
    limitations = @('File/link/ZIP and dependency checks do not assess artistic similarity','Original per-scene validation is historical; separate relocation reports record current checks')
}
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding utf8
$report | ConvertTo-Json -Depth 8

