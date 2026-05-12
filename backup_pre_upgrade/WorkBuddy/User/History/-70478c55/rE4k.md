# MEMORY.md - 长期记忆

## 项目概况
- A股智能选股系统 V5.0.0，路径：`c:/Users/green/WorkBuddy/20260424203734/workplace/年报/`
- 核心脚本：`stock_analyzer.py`（~990行）
- 股票列表：`xuan.txt`（435只A股）

## 代码架构要点
- `determine_industry()` 6级策略：文本解析→本地映射→二级转一级→名称规则→API补调→代码前缀
- `_FALLBACK_INDUSTRY_MAP` 和 `SECONDARY_TO_PRIMARY` 当前为空字典，需外部补充
- 评分时 `pool_values()` 排除自身股票，避免自影响排名
- Excel 输出 8 个 Sheet：综合评价结果 + 5个评级分组 + 低置信度 + 获取失败 + 统计概览

## 文档维护约定
- README.md 与代码需同步更新
- 每次重大修改后运行 `python stock_analyzer.py --test` 验证
