$skillDir = "C:\Users\green\.workbuddy\skills"

# 精确匹配实际目录名的删除列表
$toDelete = @(
    "AI绘图"
    "ArXiv论文追踪"
    "Browser (Puppeteer)"
    "Browser.cash"
    "CloudQ"
    "Deep Research"
    "Exa 网络搜索"
    "GIF搜索"
    "GitHub AI趋势追踪"
    "GitHub热门项目"
    "Impeccable（前端设计工具集）"
    "Joplin笔记管理"
    "Karpathy LLM Wiki"
    "Legal Logic Analysis"
    "NotebookLM Studio"
    "PDF 文档生成"
    "Playwright Scraper"
    "Remotion 视频创作"
    "Skill安全审计（云鼎实验室）"
    "Stealth Browser"
    "Tavily AI Search"
    "TencentOS运维助手"
    "Things任务"
    "Word 文档生成"
    "WorkRally"
    "ai-news-collectors"
    "auto-updater"
    "book2skill"
    "brave-search"
    "capability-evolver"
    "canvas-design（视觉设计）"
    "claude-team"
    "content总结"
    "daily-ai-news-skill"
    "darwin-skill"
    "douyin-downloader"
    "etf-assistant"
    "evolver"
    "fbs-bookwriter"
    "find-skill"
    "financial-literacy"
    "free-ride"
    "github"
    "github-ai-trends"
    "image"
    "lancedb-memory"
    "log-analyzer"
    "memory-hygiene"
    "multi-search-engine"
    "news-summary"
    "ontology"
    "openLesson"
    "self-improving"
    "self-improving-proactive-agent"
    "self-reflection"
    "senior-architect"
    "summarize"
    "superpowers"
    "task-status"
    "tecent-finance"
    "tencent-weather"
    "token-optimizer"
    "topnews"
    "tutor-skills"
    "tushare-finance"
    "valuation-analysis"
    "web-search"
    "word-docx"
    "x-longform-post"
    "yt-competitive-analysis"
    "章节正文生成器"
    "创业可以学"
    "创业验证"
    "反蒸馏"
    "市场调研"
    "提示词工程专家"
    "女娲"
    "全栈开发"
    "前端开发"
    "邮件管理"
    "智能体邮箱"
    "腾讯乐享"
    "腾讯新闻"
    "腾讯技术公益智能助手"
    "财报追踪"
    "宏观数据监控"
    "金数据"
    "笔记搜索"
)

$deleted = @()
$failed = @()
$notFound = @()

foreach ($name in $toDelete) {
    $path = Join-Path $skillDir $name
    if (Test-Path $path) {
        try {
            Remove-Item $path -Recurse -Force
            $deleted += $name
            Write-Output "DELETED: $name"
        } catch {
            $failed += $name
            Write-Output "FAILED: $name - $_"
        }
    } else {
        $notFound += $name
        Write-Output "NOT FOUND: $name"
    }
}

Write-Output ""
Write-Output "=== Summary ==="
Write-Output "Deleted: $($deleted.Count)"
Write-Output "Failed: $($failed.Count)"
Write-Output "Not found: $($notFound.Count)"

$remaining = (Get-ChildItem $skillDir -Directory).Count
Write-Output "Remaining skills: $remaining"
