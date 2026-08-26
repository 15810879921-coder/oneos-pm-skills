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

$contracts = @(
    [pscustomobject]@{
        Name = 'yunxiao-development-delivery'
        Skill = 'skills\yunxiao-development-delivery\SKILL.md'
        Metadata = 'skills\yunxiao-development-delivery\agents\openai.yaml'
        Routing = 'skills\yunxiao-development-delivery\references\semantic-routing.md'
        Selector = '$yunxiao-development-delivery'
    },
    [pscustomobject]@{
        Name = 'YunxiaoQA'
        Skill = 'skills\YunxiaoQA\SKILL.md'
        Metadata = 'skills\YunxiaoQA\agents\openai.yaml'
        Routing = 'skills\YunxiaoQA\references\semantic-routing.md'
        Selector = '$YunxiaoQA'
    }
)
$onlineInstallPage = Join-Path $RepositoryRoot 'docs\index.html'
if (-not (Test-Path -LiteralPath $onlineInstallPage)) {
    throw "缺少线上安装页：$onlineInstallPage"
}
$onlineInstallContent = Get-Content -LiteralPath $onlineInstallPage -Raw -Encoding utf8

foreach ($contract in $contracts) {
    $skillPath = Join-Path $RepositoryRoot $contract.Skill
    $metadataPath = Join-Path $RepositoryRoot $contract.Metadata
    $routingPath = Join-Path $RepositoryRoot $contract.Routing
    foreach ($path in @($skillPath, $metadataPath, $routingPath)) {
        if (-not (Test-Path -LiteralPath $path)) {
            throw "$($contract.Name) 缺少语义路由契约文件：$path"
        }
    }

    $skill = Get-Content -LiteralPath $skillPath -Raw -Encoding utf8
    $metadata = Get-Content -LiteralPath $metadataPath -Raw -Encoding utf8
    $routing = Get-Content -LiteralPath $routingPath -Raw -Encoding utf8
    if ($skill -notmatch 'semantic-routing\.md') {
        throw "$($contract.Name) 未从SKILL.md路由到semantic-routing.md"
    }
    if ($metadata -notmatch '(?ms)^policy:\s*\r?\n\s+allow_implicit_invocation:\s*true\s*$') {
        throw "$($contract.Name) 未显式启用隐式调用"
    }
    foreach ($required in @('唯一候选', '零候选', '多个候选', '零写入', $contract.Selector)) {
        if (-not $routing.Contains($required)) {
            throw "$($contract.Name) 语义路由缺少约束：$required"
        }
    }
    $onlineCommand = "npx skills add 15810879921-coder/oneos-pm-skills --skill $($contract.Name)"
    if (([regex]::Matches($onlineInstallContent, [regex]::Escape($onlineCommand))).Count -lt 2) {
        throw "$($contract.Name) 的线上安装和更新入口未统一指向用户级合集发布源"
    }
}

Write-Output '开发与测试 Skill 的主动识别、隐式调用和唯一任务路由契约完整。'
