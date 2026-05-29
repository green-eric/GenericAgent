# R177 | 2026-05-18 | 维护 | update_index.py增强-自动分类+关键词+交叉引用

## 摘要
自主行动 R177：将 update_index.py 从基础版升级为知识图谱索引，新增自动分类、关键词提取和交叉引用检测三大功能。

## 背景
原 update_index.py 仅提取报告的文件名、日期、type 字段写入 index.json。TODO P2 要求增加：
- categories 字段：自动分类
- keywords 提取
- cross-references 字段：交叉引用

## 执行过程

### 1. 探测阶段
- 运行原始 update_index.py（修复 GBK 编码问题后成功运行）
- 基线：117 个报告，已有 categories 字段（空），无 cross_references 和 keywords_cloud
- 分析了报告内容结构：标题格式 `RXX | date | type | 摘要`，正文含关键词如"回测"、"IC"、"因子"等

### 2. 增强内容

#### 自动分类 (auto_categorize)
定义了 9 个类别的规则关键词：
- 回测: 回测/IC/夏普/回撤/净值/持仓/调仓/持有期/ICIR/因子
- 数据: 数据/回填/断档/覆盖/quotes/scores表/stock_data/pe_ttm/total_mv
- 策略: 策略/融合/RPS/ScoreSys/选股/参数优化/top_n/min_score
- 因子: 因子/alpha/reversal/动量/波动率/regime/AlphaTrading/Alpha191
- 系统: 定时任务/proxy/监控/crontab/计划任务/scheduled/supervisor
- 维护: 维护/修复/日志/索引/update_index/增强/整理
- 分析: 分析/诊断/评估/规划/实测/验证
- 工具: 工具/脚本/自动化/CDP/浏览器/adb
- 记忆: 记忆/SOP/global_mem/索引/知识库

#### 关键词提取 (extract_keywords)
定义了 35+ 个领域关键词，从标题+类型+正文前500字中提取匹配项。

#### 交叉引用检测 (detect_cross_references)
两种检测策略：
1. 显式引用：扫描正文中的 R\d+ 格式引用（如 "详见 R85"）
2. 关键词重叠：两个报告共同关键词 ≥3 个则判定为 related

### 3. 修复
- 修复 SyntaxWarning: invalid escape sequence `\d` → `\\d`

## 结果

```
index.json updated: 117 reports
Categories: {'回测': 83, '分析': 76, '策略': 69, '数据': 57, '因子': 45,
             '维护': 39, '工具': 25, '系统': 22, '记忆': 11, '其他': 3}
Cross-references: 1317
Top keywords: [('scores', 64), ('ScoreSys', 62), ('IC', 61), ('因子', 40),
               ('回测', 37), ('验证', 34), ('自主行动', 29), ('修复', 26),
               ('TODO', 26), ('Python', 19)]
```

## 验收
- ✅ index.json 包含 categories 字段（10个类别）
- ✅ index.json 包含 cross_references 字段（1317条）
- ✅ index.json 包含 keywords_cloud 字段（Top 50）
- ✅ 每个报告条目包含 categories 和 keywords 数组
- ✅ 脚本可重复运行无报错

## 其他发现
- backfill_v2.py 和 fusion_picker_v2.py 均正常（无null bytes，可import），TODO "损坏文件修复" 已过时
- pe_ttm 断档 (2023-05~12) 无法通过前向填充修复：所有4344只股票的pe_ttm最早日期都在断档开始之后，无种子数据
