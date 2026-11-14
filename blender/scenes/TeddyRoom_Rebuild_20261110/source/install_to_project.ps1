param([Parameter(Mandatory=$true)][string]$UpdatesRoot)
$ErrorActionPreference='Stop'
$project='D:\codex\blender'
$caseName='TeddyRoom_Rebuild_20261110'
$caseRoot=Split-Path -Parent $PSScriptRoot
$target=Join-Path $project "scenes\$caseName"
$updates=$UpdatesRoot
if (Test-Path -LiteralPath $target) { throw 'Destination already exists; inspect before overwriting.' }
$check=Get-Content -LiteralPath (Join-Path $caseRoot 'delivery_check.json') -Raw | ConvertFrom-Json
if (-not $check.passed) {throw 'Staging validation has not passed.'}
$records=Get-Content -LiteralPath (Join-Path $updates 'before_hashes.json') -Raw | ConvertFrom-Json
foreach($r in $records){
    if((Get-FileHash -LiteralPath (Join-Path $project $r.relative) -Algorithm SHA256).Hash -ne $r.before_sha256){throw "Project document changed concurrently: $($r.relative)"}
}
Copy-Item -LiteralPath $caseRoot -Destination $target -Recurse
$copied=0
foreach($file in Get-ChildItem -LiteralPath $caseRoot -Recurse -File){
    $relative=$file.FullName.Substring($caseRoot.Length).TrimStart('\')
    if((Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath (Join-Path $target $relative) -Algorithm SHA256).Hash){throw "Copy hash mismatch: $relative"}
    $copied++
}
foreach($r in $records){Copy-Item -LiteralPath (Join-Path $updates $r.relative) -Destination (Join-Path $project $r.relative) -Force}
Copy-Item -LiteralPath (Join-Path $caseRoot 'assets\VISIBLE_CONTENT_GATE.md') -Destination "$project\docs\VISIBLE_CONTENT_GATE.md"
$blender='D:\Program Files\Blender Foundation\Blender 4.2\blender.exe'
& $blender --background "$target\scene_cycles.blend" --python-exit-code 1 --python "$target\source\deliver.py" -- verify *> "$target\verify_after_copy.log"
if($LASTEXITCODE -ne 0){throw 'Relocated Cycles reopen failed.'}
& $blender --background "$target\scene_realtime.blend" --python-exit-code 1 --python "$target\source\check_realtime.py" *> "$target\realtime_verify_after_copy.log"
if($LASTEXITCODE -ne 0){throw 'Relocated realtime reopen failed.'}
& (Join-Path $project 'tools\build_learning_packages.ps1')
& (Join-Path $project 'tools\verify_project.ps1')
[ordered]@{installed_at=(Get-Date -Format o);copied_files_hash_verified=$copied;destination=$target;reopened_at_destination=$true;previous_scene_modified=$false} | ConvertTo-Json | Set-Content -LiteralPath "$project\docs\TeddyRoom_Rebuild_20261110_install.json" -Encoding utf8
Write-Output 'INSTALL_COMPLETE'
