[CmdletBinding()]
param(
    [string]$RepositoryRoot
)

$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($RepositoryRoot)) {
    $RepositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
}
else {
    $RepositoryRoot = [System.IO.Path]::GetFullPath($RepositoryRoot)
}

$targetSkills = @(
    'YunxiaoPM',
    'yunxiao-development-delivery',
    'development-brain',
    'YunxiaoQA',
    'yunxiao-release-operations'
)
$expectedMarker = '## 每日首次自动更新（强制，先于其他动作）'
$expectedCommand = 'scripts/ensure-daily-skill-update.mjs --current-skill'
$hashes = New-Object 'System.Collections.Generic.List[string]'

foreach ($skillName in $targetSkills) {
    $skillRoot = Join-Path (Join-Path $RepositoryRoot 'skills') $skillName
    $entrypoint = Join-Path $skillRoot 'SKILL.md'
    $updater = Join-Path $skillRoot 'scripts\ensure-daily-skill-update.mjs'
    if (-not (Test-Path -LiteralPath $entrypoint -PathType Leaf)) {
        throw "缺少 Skill 入口：$entrypoint"
    }
    if (-not (Test-Path -LiteralPath $updater -PathType Leaf)) {
        throw "缺少每日更新器：$updater"
    }
    $content = Get-Content -LiteralPath $entrypoint -Raw -Encoding utf8
    if (-not $content.Contains($expectedMarker)) {
        throw "$skillName 未声明每日首次自动更新强制门禁。"
    }
    if (-not $content.Contains("$expectedCommand $skillName")) {
        throw "$skillName 的每日更新命令未传入正确的 current-skill。"
    }
    [void]$hashes.Add((Get-FileHash -LiteralPath $updater -Algorithm SHA256).Hash)
}

if (($hashes | Select-Object -Unique).Count -ne 1) {
    throw '五个 Skill 携带的每日更新器内容不一致。'
}

Write-Output '五个云效生命周期 Skill 已接入一致的每日首次全局更新门禁。'
