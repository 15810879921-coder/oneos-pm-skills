[CmdletBinding()]
param(
    [string]$OutputRoot,
    [string[]]$SkillNames,

    [ValidateSet('codex', 'cursor')]
    [string[]]$Clients = @('codex')
)

$ErrorActionPreference = 'Stop'
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$globalCommandCheck = Join-Path $PSScriptRoot 'check-global-skill-commands.ps1'
& $globalCommandCheck -RepositoryRoot $repoRoot
$dailyUpdateCheck = Join-Path $PSScriptRoot 'check-daily-skill-update.ps1'
& $dailyUpdateCheck -RepositoryRoot $repoRoot
$dailyUpdateTest = Join-Path $PSScriptRoot 'test-daily-skill-update.mjs'
& node $dailyUpdateTest
if ($LASTEXITCODE -ne 0) {
    throw "每日首次 Skill 更新行为测试失败，退出码：$LASTEXITCODE"
}
$semanticRoutingCheck = Join-Path $PSScriptRoot 'check-semantic-routing.ps1'
& $semanticRoutingCheck -RepositoryRoot $repoRoot
if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $OutputRoot = Join-Path $repoRoot 'packages'
}
$skillsRoot = Join-Path $repoRoot 'skills'
$resolvedOutput = [System.IO.Path]::GetFullPath($OutputRoot)
$allSkillNames = @(
    'AutoRDO',
    'oneos-autoprd',
    'YunxiaoPM',
    'yunxiao-development-delivery',
    'development-brain',
    'YunxiaoQA',
    'yunxiao-release-operations'
)
if ($null -eq $SkillNames -or $SkillNames.Count -eq 0) {
    $skillNames = $allSkillNames
}
else {
    $skillNames = @($SkillNames | Select-Object -Unique)
    $unknown = @($skillNames | Where-Object { $_ -notin $allSkillNames })
    if ($unknown.Count -gt 0) {
        throw "不支持的 Skill：$($unknown -join ', ')"
    }
}

$tempBase = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
$tempRoot = Join-Path $tempBase ('oneos-lifecycle-skills-' + [guid]::NewGuid().ToString('N'))
if (-not ([System.IO.Path]::GetFullPath($tempRoot)).StartsWith($tempBase, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "临时目录不在系统临时根目录内：$tempRoot"
}

New-Item -ItemType Directory -Path $resolvedOutput -Force | Out-Null
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null

try {
    foreach ($client in @($Clients | Select-Object -Unique)) {
        $clientOutput = Join-Path $resolvedOutput $client
        New-Item -ItemType Directory -Path $clientOutput -Force | Out-Null
        $manifestPath = Join-Path $clientOutput 'manifest.json'
        $manifest = New-Object 'System.Collections.Generic.List[object]'
        if (Test-Path -LiteralPath $manifestPath) {
            $existingManifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding utf8 | ConvertFrom-Json
            foreach ($entry in $existingManifest) {
                [void]$manifest.Add($entry)
            }
        }

        foreach ($skillName in $skillNames) {
            $source = Join-Path $skillsRoot $skillName
            if (-not (Test-Path -LiteralPath (Join-Path $source 'SKILL.md'))) {
                throw "缺少 Skill：$source"
            }

            $stageRoot = Join-Path $tempRoot $client
            $stageSkill = Join-Path $stageRoot $skillName
            New-Item -ItemType Directory -Path $stageRoot -Force | Out-Null
            Copy-Item -LiteralPath $source -Destination $stageRoot -Recurse -Force

            Get-ChildItem -LiteralPath $stageSkill -Directory -Recurse -Force |
                Where-Object { $_.Name -eq '__pycache__' } |
                Sort-Object FullName -Descending |
                Remove-Item -Recurse -Force
            Get-ChildItem -LiteralPath $stageSkill -File -Recurse -Force |
                Where-Object { $_.Extension -in @('.pyc', '.pyo') } |
                Remove-Item -Force

            if ($client -eq 'cursor') {
                $codexMetadata = Join-Path $stageSkill 'agents'
                if (Test-Path -LiteralPath $codexMetadata) {
                    Remove-Item -LiteralPath $codexMetadata -Recurse -Force
                }
            }

            $archive = Join-Path $clientOutput ($skillName + '.zip')
            if (Test-Path -LiteralPath $archive) {
                Remove-Item -LiteralPath $archive -Force
            }
            Compress-Archive -LiteralPath $stageSkill -DestinationPath $archive -CompressionLevel Optimal
            $hash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
            foreach ($existing in @($manifest | Where-Object { $_.skill -eq $skillName })) {
                [void]$manifest.Remove($existing)
            }
            [void]$manifest.Add([pscustomobject][ordered]@{
                client = $client
                skill = $skillName
                archive = [System.IO.Path]::GetFileName($archive)
                sha256 = $hash
            })
        }

        @($manifest.ToArray()) | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifestPath -Encoding utf8
    }
}
finally {
    $resolvedTemp = [System.IO.Path]::GetFullPath($tempRoot)
    if ($resolvedTemp.StartsWith($tempBase, [System.StringComparison]::OrdinalIgnoreCase) -and
        (Split-Path -Leaf $resolvedTemp).StartsWith('oneos-lifecycle-skills-', [System.StringComparison]::OrdinalIgnoreCase) -and
        (Test-Path -LiteralPath $resolvedTemp)) {
        Remove-Item -LiteralPath $resolvedTemp -Recurse -Force
    }
}

Write-Output "已生成客户端包 [$(@($Clients | Select-Object -Unique) -join ', ')]：$resolvedOutput"
