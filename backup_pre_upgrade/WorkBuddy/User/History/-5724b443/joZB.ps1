[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$skillDir = "C:\Users\green\.workbuddy\skills"

# 获取所有技能目录
$allSkills = Get-ChildItem $skillDir -Directory

# 保留列表（白名单）
$keep = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
$keepNames = @(
    "stock-analysis-23","stock-analyst","stock-board","stock-info-explorer",
    "stock-market-pro","stock-monitor","stock-predictor","stock-price-query",
    "stock-proactive-daily-briefing","stock-selecter","stock","stockclaw-yingyan3",
    "ths-advanced-analysis","ths-financial-data","trading","technical-analyst",
    "akshare-finance","akshare-stock","eastmoney-fin-search","eastmoney-tools",
    "finance-data-fetcher","finance-ops","finance-report-assistant",
    "finance-research-report","finance","finance-bp-core",
    "NeoData金融搜索服务","china-stock-analysis","WeStock Data","openclaw-stock-data-skill",
    "web-search","Excel 文件处理","PPT 演示文稿","MarkItDown",
    "Agent Browser Core","Playwright Browser Automation",
    "code","coding","AI交叉审查",
    "self-improving-agent","self-improving-agent-cn",
    "自己.skill","find-skills","tencentmap-lbs-skill","news-summary",
    "Agent Team Orchestration","multi-search-engine","find-skill","log-analyzer",
    "memory-hygiene","lancedb-memory","Karpathy LLM Wiki",
    "提示词工程专家","autoresearch","Deep Research","book2skill","token-optimizer",
    "AI绘图","canvas-design（视觉设计）","Remotion 视频创作","GIF搜索","image",
    "Impeccable（前端设计工具集）","前端开发","全栈开发","CloudQ",
    "TencentOS运维助手","邮件管理","智能体邮箱",
    "腾讯ima","腾讯ima-backup-20260418","腾讯乐享","腾讯新闻","腾讯技术公益智能助手",
    "Skill安全审计（云鼎实验室）","senior-architect","superpowers","task-status",
    "claude-team","topnews","ArXiv论文追踪","x-longform-post","章节正文生成器",
    "fbs-bookwriter","女娲","创业可以学","创业验证","市场调研","反蒸馏",
    "financial-literacy","yt-competitive-analysis","douyin-downloader","NotebookLM Studio",
    "Legal Logic Analysis","WorkRally","tutor-skills","openLesson",
    "model-usage","模型用量统计","things","Joplin笔记管理",
    "笔记搜索","自己.skill","财报追踪","宏观数据监控","金数据",
    "etf-assistant","tecent-finance","tushare-finance","valuation-analysis",
    "github","github-ai-trends","GitHub AI趋势追踪","GitHub热门项目",
    "ai-news-collectors","daily-ai-news-skill","news-summary","content总结","summarize",
    "MarkItDown","PDF 文档生成","Word 文档生成","word-docx",
    "Agent Browser Core","Browser (Puppeteer)","Playwright Browser Automation",
    "Playwright Scraper","Stealth Browser","Browser.cash",
    "Web Access（浏览器自动化）","Web Scraper","web-search","multi-search-engine",
    "Exa 网络搜索","brave-search","tavily-search","Tavily AI Search",
    "auto-updater","capability-evolver","darwin-skill","autoresearch","book2skill",
    "token-optimizer","free-ride","evolver","find-skill","find-skills",
    "self-improving-agent","self-improving-agent-cn","self-improving-proactive-agent",
    "self-improving","self-reflection","memory-hygiene","lancedb-memory",
    "Karpathy LLM Wiki","log-analyzer","ontology","batch-plot"
)
foreach ($k in $keepNames) { [void]$keep.Add($k) }

Write-Output "Keep count: $($keep.Count)"
Write-Output ""

$deleted = @()
$failed = @()

foreach ($skill in $allSkills) {
    if (-not $keep.Contains($skill.Name)) {
        $path = $skill.FullName
        try {
            Remove-Item $path -Recurse -Force
            $deleted += $skill.Name
            Write-Output "DELETED: $($skill.Name)"
        } catch {
            $failed += $skill.Name
            Write-Output "FAILED: $($skill.Name) - $_"
        }
    } else {
        Write-Output "KEEP: $($skill.Name)"
    }
}

Write-Output ""
Write-Output "=== Summary ==="
Write-Output "Deleted: $($deleted.Count)"
Write-Output "Failed: $($failed.Count)"
$remaining = (Get-ChildItem $skillDir -Directory).Count
Write-Output "Remaining: $remaining"
