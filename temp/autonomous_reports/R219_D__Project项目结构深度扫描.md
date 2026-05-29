# D:/Project 项目结构深度扫描报告
**日期**: 2026-05-20  
**扫描范围**: D:/Project 下所有项目目录  

## 项目地图

### 📦 3个项目 | 1425.4MB

| 项目 | 类型 | 大小 | 子目录 | 关键文件 |
|------|------|------|--------|----------|
| BfM | Node.js/Python | 0.77MB | 21个 | config.yaml, CONFIG_DOC.md, .env |
| AnnualScorer | Python | 4.4MB | 11个 | config.py, pyproject.toml, README.md |
| ScoreSys | Python | 1420.26MB | 20个 | config.py, config.ini |

---

## 项目详情

### 1. BfM (A股利好监控系统)
- **类型**: Node.js + Python 混合
- **版本**: 10.1
- **配置**: config.yaml + config/目录(10个YAML)
- **功能**: A股利好监控、交易信号、飞书推送
- **关键配置域**:
  - scoring.yaml - 评分权重
  - trading.yaml - 交易策略/风控
  - pipeline.yaml - 流水线
  - feishu.yaml - 飞书推送
  - keywords.yaml - 板块/情绪关键词
- **环境变量**: VITE_API_BASE_URL, FEISHU_WEBHOOK, API_KEY
- **子目录**: config/, data/, docs/, 等

### 2. AnnualScorer (A股智能选股系统)
- **类型**: Python
- **数据库**: annual_scorer.db (SQLite, 24KB)
- **核心文件**: annual_scorer.py, api_client.py, config.py, db.py
- **功能**: 智能选股、API客户端、数据库管理
- **工具链**: .github/workflows, .sisyphus, .workbuddy

### 3. ScoreSys (评分系统)
- **类型**: Python
- **大小**: 1.4GB (最大项目)
- **配置**: config.py, config.ini
- **子目录**: 20个

---

## 集成建议

### 高价值发现
1. **BfM + GA集成**: BfM的飞书推送和交易信号可接入GA的EventBus
2. **AnnualScorer数据库**: SQLite数据库可迁移到Redis做缓存加速
3. **ScoreSys评分引擎**: 1.4GB项目，可能是核心评分引擎，值得深入分析

### 可复用组件
- BfM的config/目录结构(10个YAML配置)可作为GA配置管理参考
- AnnualScorer的api_client.py可复用为GA的API调用模板
- ScoreSys的config.py配置模式

### 待深入
- ScoreSys子目录详情(20个子目录，1.4GB)
- BfM的data/目录数据结构
- AnnualScorer的.sisyphus/和.workbuddy/工具链

---

**结论**: D:/Project包含3个A股相关项目，BfM是完整的监控系统，AnnualScorer是选股工具，ScoreSys是核心评分引擎。与GA的EventBus和Redis有天然集成点。