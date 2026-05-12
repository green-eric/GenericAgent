# 核心保留：股票分析、金融数据、搜索、文档、开发、AI辅助
$keep = @(
    # === 股票/金融分析（核心） ===
    "stock-analysis-23","stock-analyst","stock-board","stock-info-explorer",
    "stock-market-pro","stock-monitor","stock-predictor","stock-price-query",
    "stock-proactive-daily-briefing","stock-selecter","stock","stockclaw-yingyan3",
    "akshare-finance","akshare-stock","china-stock-analysis",
    "eastmoney-fin-search","eastmoney-tools","etf-assistant",
    "finance-data-fetcher","finance-news-analyzer","finance-news-pro",
    "finance-ops","finance-report-assistant","finance-research-report",
    "finance","finance-bp-core","NeoData金融搜索服务",
    "openclaw-stock-data-skill","tecent-finance",
    "ths-advanced-analysis","ths-financial-data","tushare-finance",
    "valuation-analysis","WeStock Data","trading","technical-analyst",
    "财报追踪","宏观数据监控","金数据",
    # === 搜索 ===
    "multi-search-engine","Exa 网络搜索","brave-search",
    "tavily-search","Tavily AI Search","web-search",
    # === 文档处理 ===
    "PDF 文档生成","Excel 文件处理","PPT 演示文稿",
    "Word 文档生成","word-docx","MarkItDown","content总结","summarize",
    # === 浏览器自动化 ===
    "Agent Browser Core","Playwright Browser Automation","Playwright Scraper",
    "Stealth Browser","Browser (Puppeteer)","Browser.cash",
    "Web Access（浏览器自动化）","Web Scraper",
    # === 开发 ===
    "code","coding","senior-architect","前端开发","全栈开发",
    "Agent Team Orchestration","superpowers","task-status",
    "AI交叉审查","log-analyzer",
    # === AI/记忆 ===
    "self-improving-agent","self-improving-agent-cn",
    "self-improving-proactive-agent","self-improving","self-reflection",
    "memory-hygiene","lancedb-memory","Karpathy LLM Wiki",
    "提示词工程专家","autoresearch","Deep Research","book2skill",
    "token-optimizer","AI绘图","find-skill","find-skills","auto-updater",
    # === 笔记/知识 ===
    "笔记搜索","Joplin笔记管理","自己.skill",
    # === 通讯/社交 ===
    "腾讯ima","腾讯ima-backup-20260418","腾讯乐享","腾讯新闻",
    "腾讯技术公益智能助手","邮件管理","智能体邮箱",
    # === 工具 ===
    "tencentmap-lbs-skill","tencent-weather",
    "GitHub热门项目","github-ai-trends","GitHub AI趋势追踪",
    "ai-news-collectors","daily-ai-news-skill","news-summary",
    "模型用量统计","free-ride","capability-evolver","darwin-skill",
    "GIF搜索","image","Remotion 视频创作",
    "女娲","创业可以学","创业验证","市场调研","反蒸馏",
    "Skill安全审计（云鼎实验室）","TencentOS运维助手",
    "topnews","ArXiv论文追踪","x-longform-post",
    "章节正文生成器","fbs-bookwriter","financial-literacy",
    "yt-competitive-analysis","douyin-downloader","NotebookLM Studio",
    "Legal Logic Analysis","WorkRally","tutor-skills","openLesson",
    "Impeccable（前端设计工具集）","canvas-design（视觉设计）",
    "CloudQ","Things任务","ontology","claude-team","evolver",
    "batch-plot"  # 如果有批量绘图需求
)

$skillDir = "C:\Users\green\.workbuddy\skills"
$allSkills = Get-ChildItem $skillDir -Directory | Select-Object Name

$toRemove = @()
$toKeep = @()

foreach ($s in $allSkills) {
    $matched = $false
    foreach ($k in $keep) {
        if ($s.Name -eq $k) { $matched = $true; break }
    }
    if ($matched) { $toKeep += $s.Name } else { $toRemove += $s.Name }
}

Write-Output "=== KEEP ($($toKeep.Count)) ==="
foreach ($s in $toKeep | Sort-Object) { Write-Output "  [KEEP] $s" }

Write-Output ""
Write-Output "=== REMOVE ($($toRemove.Count)) ==="
foreach ($s in $toRemove | Sort-Object) { Write-Output "  [DEL] $s" }

$totalSize = 0
foreach ($s in $toRemove) {
    $path = Join-Path $skillDir $s
    $size = (Get-ChildItem $path -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    $totalSize += $size
}
Write-Output ""
Write-Output "Disk space to free: $([math]::Round($totalSize/1MB,1)) MB"
