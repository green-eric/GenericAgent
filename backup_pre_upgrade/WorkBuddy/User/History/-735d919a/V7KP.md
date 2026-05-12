# ScoreSys 项目长期记忆

## 项目基本信息
- A股智能选股系统 v3.1
- 项目路径：d:\Project\ScoreSys\
- Python路径：C:\Users\green\AppData\Local\Python\bin\python.exe
- 股票池：stock_pool.txt 包含4344只A股

## 关键架构
- 数据获取-评分解耦架构：fetch-only → from-db
- 五维评分：成长性25% + 盈利能力30% + 现金流质量20% + 偿债风险15% + 估值10%
- 数据源三级降级：全市场行情缓存 → 东方财富个股 → NeoData兜底
- 断点续传：fetch-only模式自动跳过已有≥4季度的股票

## Windows 环境踩坑
- PowerShell 不支持 `cd /d` 语法，必须用绝对路径运行 python
- subprocess 在 Windows 下 encoding='utf-8' 遇 GBK 中文会崩，改用二进制模式+decode
- NeoData脚本路径：`~/.workbuddy/plugins/marketplaces/cb_teams_marketplace/plugins/finance-data/skills/neodata-financial-search/scripts/query.py`
- npx 调用需要 shell=True

## 数据源状态（2026-04-28）
- 东方财富 stock_individual_info_em：持续被拒绝（RemoteDisconnected）
- 东方财富 stock_zh_a_spot_em：大部分时间被拒绝
- AkShare 同花顺三表（stock_financial_benefit/debt/cash_new_ths）：正常
- NeoData：正常，但每次启动Python子进程约2-3s
- westock-data profile：正常，约3-5s

## 性能参考
- 单只股票获取：财务3表约2-3s + 行情/名称约1-3s（取决于走哪个降级链）
- 4000+全量获取：workers=8，约30-60分钟
- 评分阶段：约1-2分钟
