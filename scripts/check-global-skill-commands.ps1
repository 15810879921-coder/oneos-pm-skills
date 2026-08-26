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
$commandPattern = 'npx\s+skills\s+(add|update)\b'
$skillPattern = ($targetSkills | ForEach-Object { [regex]::Escape($_) }) -join '|'
$globalPattern = '(?:^|\s)(?:-g|--global)(?:\s|$)'
$documents = @(
    (Join-Path $RepositoryRoot 'README.md'),
    (Join-Path $RepositoryRoot 'docs\index.html')
) | Where-Object { Test-Path -LiteralPath $_ }

$violations = New-Object 'System.Collections.Generic.List[string]'
foreach ($document in $documents) {
    $lineNumber = 0
    foreach ($line in Get-Content -LiteralPath $document -Encoding utf8) {
        $lineNumber++
        if ($line -notmatch $commandPattern -or $line -notmatch $skillPattern) {
            continue
        }
        if ($line -match '--list\b') {
            continue
        }
        if ($line -notmatch $globalPattern) {
            $relativePath = [System.IO.Path]::GetRelativePath($RepositoryRoot, $document)
            [void]$violations.Add("${relativePath}:${lineNumber}: $($line.Trim())")
        }
    }
}

if ($violations.Count -gt 0) {
    throw "发现未声明用户级全局范围的云效 Skill 安装或更新口令：`n$($violations -join "`n")"
}

Write-Output '云效 Skill 公开安装与更新口令均已声明用户级全局范围。'
