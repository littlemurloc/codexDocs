$ErrorActionPreference='Stop'
$stagingRoot=Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) 'TeddyRoom_Rebuild_20261110_project_updates'
New-Item -ItemType Directory -Force -Path $stagingRoot | Out-Null
$project='D:\codex\blender'
$records=@()
function Stage-Update([string]$Relative,[string]$Content) {
    $target=Join-Path $stagingRoot $Relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
    Set-Content -LiteralPath $target -Value $Content -Encoding utf8
    $script:records += [pscustomobject]@{relative=$Relative;before_sha256=(Get-FileHash -LiteralPath (Join-Path $project $Relative) -Algorithm SHA256).Hash}
}
$agent=Get-Content -LiteralPath "$project\AGENTS.md" -Raw
$agent+="`n## 可见内容保留门槛（2026-11-10 增补）`n`n开工还须阅读 [VISIBLE_CONTENT_GATE.md](docs/VISIBLE_CONTENT_GATE.md)。按物件记录原图可见轮廓、数量、图案和排列；分别检查对象存在、外观保留和成片可见。可见部分按证据保留，隐藏部分才设计补全。主资产占位不得自动通过最终外观验收。`n"
Stage-Update 'AGENTS.md' $agent
$pipeline=Get-Content -LiteralPath "$project\docs\PIPELINE.md" -Raw
$pipeline+="`n## 2026-11-10 增补：可见内容的逐物件验收`n`n本流程同时执行 [可见内容保留门槛](VISIBLE_CONTENT_GATE.md)。新建 [熊房间重建案例](../scenes/TeddyRoom_Rebuild_20261110/README.md) 展示从空场景执行；原案例保留为对照，不覆盖。清点与外观门槛分别加入分析、白模、资产和最终渲染阶段，不能仅在最后查对象数。`n"
Stage-Update 'docs\PIPELINE.md' $pipeline
$readme=Get-Content -LiteralPath "$project\README.md" -Raw
$readme=$readme.Replace('目前有两套学习原型','目前有三套学习案例（包含室内的两次独立制作）')
$readme+="`n## 2026-11-10：同一熊房间从空场景重建`n`n新增 [三图与工序预览](scenes/TeddyRoom_Rebuild_20261110/index.html)、[制作说明](scenes/TeddyRoom_Rebuild_20261110/README.md)、[Cycles 工程](scenes/TeddyRoom_Rebuild_20261110/scene_cycles.blend)、[实时版](scenes/TeddyRoom_Rebuild_20261110/scene_realtime.blend)、[学习包](learning/packages/TeddyRoom_Rebuild_20261110_完整学习包.zip)。本版没有加载或修改第一版 3D 工程。重点增加可见物件清单、外观保留、原纸画内容与逐项视觉复核。新门槛见 [VISIBLE_CONTENT_GATE.md](docs/VISIBLE_CONTENT_GATE.md)。`n"
Stage-Update 'README.md' $readme
$build=Get-Content -LiteralPath "$project\tools\build_learning_packages.ps1" -Raw
$build=$build.Replace("@('TeddyRoom_Study', 'SakuraLane_Study')","@('TeddyRoom_Study', 'SakuraLane_Study', 'TeddyRoom_Rebuild_20261110')")
Stage-Update 'tools\build_learning_packages.ps1' $build
$verify=Get-Content -LiteralPath "$project\tools\verify_project.ps1" -Raw
$verify=$verify.Replace("@('TeddyRoom_Study','SakuraLane_Study')","@('TeddyRoom_Study','SakuraLane_Study','TeddyRoom_Rebuild_20261110')")
Stage-Update 'tools\verify_project.ps1' $verify
$records | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $stagingRoot 'before_hashes.json') -Encoding utf8
Write-Output $stagingRoot
