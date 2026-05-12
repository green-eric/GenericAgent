$skillDir = "C:\Users\green\.workbuddy\skills"

# 建议删除的技能（151个中删掉这些，保留约30个核心）
$remove = @(
    "AI绘图"                              # 不常用
    "ArXiv论文追踪"                       # 学术用不上
    "Browser (Puppeteer)"                  # 已有Playwright
    "Browser.cash"                         # 已有其他浏览器工具
    "CloudQ"                               # 不明确用途
    "Deep Research"                        # 已有autoresearch
    "Exa 网络搜索"                         # 已有多个搜索工具
    "GIF搜索"                              # 不常用
    "GitHub AI趋势追踪"                    # 已有github-ai-trends
    "GitHub热门项目"                       # 重复
    "Impeccable（前端设计工具集）"         # 不常用
    "Joplin笔记管理"                       # 已有笔记搜索
    "Karpathy LLM Wiki"                    # 不常用
    "Legal Logic Analysis"                 # 用不上
    "NotebookLM Studio"                    # 不常用
    "PDF 文档生成"                         # 已有轻量PDF编辑器
    "Playwright Scraper"                   # 已有Playwright Browser Automation
    "Remotion 视频创作"                    # 不常用
    "Skill安全审计（云鼎实验室）"          # 偶尔用，可临时装
    "Stealth Browser"                      # 已有其他浏览器工具
    "Tavily AI Search"                     # 已有tavily-search
    "TencentOS运维助手"                    # 用不上
    "Things任务"                           # macOS only
    "Word 文档生成"                        # 已有word-docx
    "WorkRally"                            # 不明确
    "ai-news-collectors"                   # 已有daily-ai-news-skill
    "auto-updater"                         # 系统自带
    "batch-plot"                           # 不常用
    "book2skill"                           # 不常用
    "brave-search"                         # 已有multi-search-engine
    "capability-evolver"                   # 不常用
    "canvas-design（视觉设计）"            # 不常用
    "chapter-generator"                    # 不常用
    "claude-team"                          # 用不上
    "content总结"                          # 已有summarize
    "daily-ai-news-skill"                  # 已有news-summary
    "darwin-skill"                         # 不常用
    "douyin-downloader"                    # 用不上
    "etf-assistant"                        # 已有股票分析工具覆盖
    "evolver"                              # 不常用
    "fbs-bookwriter"                        # 不常用
    "find-skill"                           # 已有find-skills
    "financial-literacy"                   # 用不上
    "free-ride"                            # 不常用
    "github"                               # 已有GitHub相关工具
    "github-ai-trends"                     # 已有GitHub AI趋势追踪
    "image"                                # 不常用
    "lancedb-memory"                       # 已有memory-hygiene
    "log-analyzer"                         # 不常用
    "memory-hygiene"                       # 偶尔用
    "model-usage"                          # 已有模型用量统计
    "multi-search-engine"                  # 搜索工具太多，保留一个即可
    "news-summary"                         # 已有ai-news-collectors
    "ontology"                             # 不常用
    "openLesson"                           # 用不上
    "self-improving"                        # 已有self-improving-agent
    "self-improving-proactive-agent"       # 已有self-improving-agent-cn
    "self-reflection"                      # 已有self-improving-agent
    "senior-architect"                     # 已有code/coding
    "summarize"                            # 已有content总结
    "superpowers"                          # 已有code
    "task-status"                          # 不常用
    "tecent-finance"                       # 已有多个金融数据工具
    "tencent-weather"                      # 不常用
    "token-optimizer"                      # 不常用
    "topnews"                              # 已有新闻工具
    "tutor-skills"                         # 用不上
    "tushare-finance"                      # 已有akshare覆盖
    "valuation-analysis"                   # 已有stock-analysis覆盖
    "web-search"                           # 已有多个搜索工具
    "word-docx"                            # 已有Word 文档生成
    "x-longform-post"                      # 不常用
    "yt-competitive-analysis"              # 用不上
    "章节正文生成器"                       # 不常用
    "创业可以学"                           # 不常用
    "创业验证"                             # 不常用
    "反蒸馏"                               # 不常用
    "市场调研"                             # 不常用
    "提示词工程专家"                       # 不常用
    "女娲"                                 # 不常用
    "全栈开发"                             # 已有前端开发+code
    "前端开发"                             # 已有code/coding
    "邮件管理"                             # 用不上
    "智能体邮箱"                           # 用不上
    "腾讯乐享"                             # 用不上
    "腾讯新闻"                             # 不常用
    "腾讯技术公益智能助手"                 # 用不上
    "财报追踪"                             # 已有股票分析工具
    "宏观数据监控"                         # 已有金融数据工具
    "金数据"                               # 不常用
)

$allSkills = Get-ChildItem $skillDir -Directory | Select-Object Name

$confirmedRemove = @()
$notFound = @()

foreach ($r in $remove) {
    $found = $false
    foreach ($s in $allSkills) {
        if ($s.Name -eq $r) { $found = $true; break }
    }
    if ($found) { $confirmedRemove += $r } else { $notFound += $r }
}

$remaining = @()
foreach ($s in $allSkills) {
    $inRemove = $false
    foreach ($r in $confirmedRemove) {
        if ($s.Name -eq $r) { $inRemove = $true; break }
    }
    if (-not $inRemove) { $remaining += $s.Name }
}

Write-Output "=== 建议删除 ($($confirmedRemove.Count) 个) ==="
foreach ($s in $confirmedRemove | Sort-Object) { Write-Output "  [DEL] $s" }

Write-Output ""
Write-Output "=== 保留 ($($remaining.Count) 个) ==="
foreach ($s in $remaining | Sort-Object) { Write-Output "  [KEEP] $s" }

$totalSize = 0
foreach ($s in $confirmedRemove) {
    $path = Join-Path $skillDir $s
    if (Test-Path $path) {
        $size = (Get-ChildItem $path -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        $totalSize += $size
    }
}
Write-Output ""
Write-Output "可释放磁盘空间: $([math]::Round($totalSize/1MB,1)) MB"
