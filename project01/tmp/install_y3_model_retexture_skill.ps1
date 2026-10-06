$ErrorActionPreference = 'Stop'
$texturePython = 'C:\Users\littl\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$textureSkillSource = 'D:\codex\project01\tmp\skill-build\y3-model-retexture'
$textureSkillParent = 'D:\codex\project01\.agents\skills'
$textureSkillTarget = Join-Path $textureSkillParent 'y3-model-retexture'
if (Test-Path -LiteralPath $textureSkillTarget) {
    throw "Refusing to replace an existing skill: $textureSkillTarget"
}
& $texturePython -B -X utf8 'D:\codex\project01\tmp\test_y3_model_retexture_skill.py'
if ($LASTEXITCODE -ne 0) { throw 'Resource script verification failed' }
& $texturePython -B -X utf8 -c "import sys,runpy; sys.path.insert(0,r'C:\Users\littl\Documents\Codex\2026-10-04\bang\outputs\y3-eca-mcp\.deps'); sys.argv=['quick_validate.py',r'D:\codex\project01\tmp\skill-build\y3-model-retexture']; runpy.run_path(r'C:\Users\littl\.codex\skills\.system\skill-creator\scripts\quick_validate.py',run_name='__main__')"
if ($LASTEXITCODE -ne 0) { throw 'Skill frontmatter validation failed' }
New-Item -ItemType Directory -Path $textureSkillParent -Force | Out-Null
New-Item -ItemType Directory -Path $textureSkillTarget | Out-Null
# Copy only maintained resources, excluding Python caches from validation.
foreach ($textureSkillRelative in @('SKILL.md','agents\openai.yaml','references\cache-format.md','references\lvbu-case.md','scripts\y3_texture.py')) {
    $textureSkillSourceFile = Join-Path $textureSkillSource $textureSkillRelative
    $textureSkillTargetFile = Join-Path $textureSkillTarget $textureSkillRelative
    New-Item -ItemType Directory -Path (Split-Path -Parent $textureSkillTargetFile) -Force | Out-Null
    Copy-Item -LiteralPath $textureSkillSourceFile -Destination $textureSkillTargetFile
    if ((Get-FileHash -LiteralPath $textureSkillSourceFile).Hash -ne (Get-FileHash -LiteralPath $textureSkillTargetFile).Hash) {
        throw "Installed file differs from validated source: $textureSkillRelative"
    }
}
Write-Output "Installed project skill: $textureSkillTarget"
