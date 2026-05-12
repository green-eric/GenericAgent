# 年报与季度评分系统概览

## 系统架构总览

本系统包含两个独立但互补的评分子系统：

### 📊 年报评分系统 (V5.0.0)
- **路径**: `年报/`
- **核心文件**: `stock_analyzer.py`
- **功能**: 基于年报数据的年度业绩评分
- **特点**: 结构化段落匹配、四维评分体系、行业相对排名

### 📈 季度评分系统 (V6.0.0)
- **路径**: `季报/`
- **核心文件**: `quarterly_scorer.py`
- **功能**: 基于季度数据的短期业绩评分
- **特点**: 季度段落提取、交叉验证机制、优选股票筛选

---

## 📊 年报评分系统详细文档

请参考独立文档: [`年报/README.md`](年报/README.md)

### 核心特性
- ✅ **精确段落匹配**: 通过"统计截止日期为YYYY1231的年报"锚点定位
- ✅ **13项财务指标提取**: ROE、毛利率、净利率、营收同比、净利润同比等
- ✅ **四维评分体系**: 盈利能力(35%) + 成长性(30%) + 现金流质量(15%) + 偿债风险(20%)
- ✅ **行业相对排名**: 同行业百分位评分，小行业自动 fallback 全市场
- ✅ **完整度惩罚机制**: 高(≥85.7%)、中(57.1%)、低(<57.1%)分级惩罚
- ✅ **并发处理**: 16线程 + requests.Session连接池
- ✅ **缓存策略**: SQLite数据库，年报过期判断基于4月30日截止日

### 输出结果
- **Excel报告**: `股票业绩评价_{时间戳}.xlsx` (综合评价、分级股票、异常日志等)
- **JSON数据**: `股票分析数据_{时间戳}.json` (26个字段，按总分降序)

### 使用方式
```bash
# 运行自测
python stock_analyzer.py --test

# 完整分析
python stock_analyzer.py

# 参数说明
--workers N        # 并发线程数 (默认16)
--force-refresh    # 强制刷新缓存
--no-industry-patch # 禁用行业API补调
--timeout SECONDS  # 全局超时
```

---

## 📈 季度评分系统详细文档

请参考独立文档: [`季报/QUARTERLY_SCORING_SYSTEM_REPORT.md`](季报/QUARTERLY_SCORING_SYSTEM_REPORT.md)

### 核心特性
- ✅ **季度段落精确提取**: 正则匹配"统计截止日期为YYYYMMDD的Q[123]单季报"
- ✅ **4项关键指标解析**: 销售毛利率、销售净利率、营收同比增长、净利润同比增长
- ✅ **评分算法**: 盈利得分×35% + 成长得分×30% + 现金流得分×15% + 负债得分×20%
- ✅ **交叉验证机制**: 年报A级 ∩ 季报A级的交集筛选
- ✅ **独立设计**: 不依赖原始stock_analyzer.py，可独立运行
- ✅ **本地测试模式**: 支持--local-test避免API调用

### 测试结果
- **数据规模**: 4,344只股票，4,311条有效年报数据
- **评分分布**: 年报A级股票25.0% (1,085只)
- **验证成功率**: 100% (随机验证10只股票全部成功)

### 使用方式
```bash
# 运行自测
python quarterly_scorer.py --test

# 随机验证10只股票 (本地测试)
python quarterly_scorer.py --verify 10 --local-test

# 强制刷新季度数据
python quarterly_scorer.py --force

# 完整运行 (需要API token)
python quarterly_scorer.py
```

---

## 🔄 系统集成与协同工作

### 数据流关系
```
NeoData API
     ↓
年报评分系统 → 年报数据存储 → 季度评分系统
     ↓                              ↓
Excel/JSON报告              JSON交叉验证报告
```

### 优选股票筛选流程
1. **年报评分** → 筛选出A级股票集合
2. **季度评分** → 筛选出A级股票集合  
3. **交集计算** → 年报A级 ∩ 季报A级 = 优选股票池

### 配置管理
- **共用配置**: 股票代码列表 (`xuan.txt`)
- **共用数据库**: `stock_cache.db` (年报数据)
- **独立配置**: 各自系统的参数设置

---

## 🛠️ 技术栈对比

| 特性 | 年报系统 | 季度系统 |
|------|----------|----------|
| **主要语言** | Python | Python |
| **并发模型** | ThreadPoolExecutor | ThreadPoolExecutor |
| **网络请求** | requests.Session | requests.Session |
| **数据存储** | SQLite | SQLite |
| **API调用** | NeoData实时API | NeoData实时API |
| **评分维度** | 4D (盈利+成长+现金流+负债) | 4D (盈利+成长+现金流+负债) |
| **数据粒度** | 年度 | 季度 |
| **段落匹配** | 年报锚点匹配 | 季度正则匹配 |

---

## 📋 快速启动指南

### 年报系统启动
```bash
cd 年报/
python stock_analyzer.py --test          # 先运行自测
python stock_analyzer.py                 # 完整运行分析
```

### 季度系统启动
```bash
cd 季报/
python quarterly_scorer.py --test        # 先运行自测
python quarterly_scorer.py --verify 5    # 随机验证5只股票
python quarterly_scorer.py               # 完整运行分析
```

---

## 📚 文档导航

- [📊 年报系统详细文档](年报/README.md)
- [📈 季度系统测试报告](季报/QUARTERLY_SCORING_SYSTEM_REPORT.md)
- [📋 项目总结](季报/PROJECT_SUMMARY.md)
- [🔧 配置文件说明](#配置说明) (待完善)
- [🐛 常见问题](#常见问题) (待完善)

---

*最后更新: 2026-04-26*
*适用版本: 年报 V5.0.0 / 季度 V6.0.0*