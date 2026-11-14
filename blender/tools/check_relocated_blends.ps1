param([string]$BlenderExe = 'D:\Program Files\Blender Foundation\Blender 4.2\blender.exe')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$checks = @(
    @{ Name='teddy_cycles'; File='TeddyRoom_Study\scene.blend'; Engine='CYCLES'; Render=$true },
    @{ Name='teddy_realtime'; File='TeddyRoom_Study\scene_realtime.blend'; Engine='BLENDER_EEVEE_NEXT'; Render=$false },
    @{ Name='sakura_cycles'; File='SakuraLane_Study\scene_cycles.blend'; Engine='CYCLES'; Render=$true },
    @{ Name='sakura_realtime'; File='SakuraLane_Study\scene_realtime.blend'; Engine='BLENDER_EEVEE_NEXT'; Render=$false }
)
foreach ($check in $checks) {
    $report = Join-Path $projectRoot "docs\relocation_checks\$($check.Name).json"
    New-Item -ItemType Directory -Path (Split-Path -Parent $report) -Force | Out-Null
    $blend = Join-Path $projectRoot "scenes\$($check.File)"
    $script = Join-Path $PSScriptRoot 'verify_blender_relocation.py'
    $arguments = @('--background', $blend, '--python-exit-code', '1', '--python', $script, '--', $report, $check.Engine)
    if ($check.Render) { $arguments += '--render' }
    & $BlenderExe @arguments *> ($report + '.log')
    if ($LASTEXITCODE -ne 0) { throw "Blender verification failed; inspect $report.log" }
    Write-Output "Checked $($check.Name)"
}
