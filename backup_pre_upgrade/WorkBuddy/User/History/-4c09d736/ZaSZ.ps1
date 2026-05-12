[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$skillDir = "C:\Users\green\.workbuddy\skills"

# 只保留这35个核心技能
$keepSet = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)

$coreSkills = @(
    "akshare-finance"
    "akshare-stock"
    "AI交叉审查"
    "Agent Browser Core"
    "Agent Team Orchestration"
    "autoresearch"
    "china-stock-analysis"
    "code"
    "coding"
    "eastmoney-fin-search"
    "eastmoney-tools"
    "Excel 文件处理"
    "finance"
    "finance-bp-core"
    "finance-data-fetcher"
    "finance-ops"
    "finance-report-assistant"
    "finance-research-report"
    "find-skills"
    "MarkItDown"
    "NeoData金融搜索服务"
    "news-summary"
    "openclaw-stock-data-skill"
    "Playwright Browser Automation"
    "PPT 演示文稿"
    "self-improving-agent"
    "self-improving-agent-cn"
    "stock"
    "stock-analysis-23"
    "stock-analyst"
    "stock-board"
    "stockclaw-yingyan3"
    "stock-info-explorer"
    "stock-market-pro"
    "stock-monitor"
    "stock-predictor"
    "stock-price-query"
    "stock-proactive-daily-briefing"
    "stock-selecter"
    "technical-analyst"
    "ths-advanced-analysis"
    "ths-financial-data"
    "tencentmap-lbs-skill"
    "trading"
    "web-search"
    "WeStock Data"
    "自己.skill"
)

foreach ($k in $coreSkills) { [void]$keepSet.Add($k) }

$allSkills = Get-ChildItem $skillDir -Directory
$deleted = @()
$kept = @()
$failed = @()

foreach ($skill in $allSkills) {
    if ($keepSet.Contains($skill.Name)) {
        $kept += $skill.Name
        Write-Output "KEEP: $($skill.Name)"
    } else {
        try {
            Remove-Item $skill.FullName -Recurse -Force
            $deleted += $skill.Name
            Write-Output "DEL:  $($skill.Name)"
        } catch {
            $failed += $skill.Name
            Write-Output "FAIL: $($skill.Name)"
        }
    }
}

Write-Output ""
Write-Output "=== RESULT ==="
Write-Output "Deleted: $($deleted.Count)"
Write-Output "Kept: $($kept.Count)"
Write-Output "Failed: $($failed.Count)"
