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

## 数据字段踩坑（v3.1.1修复）
- `index_deduct_holder_net_profit`（扣非净利润）必须加入PROFIT_METRICS，否则net_profit_ex全0
- `benefit_finance_fee`（财务费用）是部分公司（如000858）的唯一财务费用字段，需作为interest_expenses的备选
- `financial_interest_expenses`与`interest_expenses`不能同时映射同一列名，否则dedup会丢失数据
- Calculator判断扣非净利润有效性：用`(df[col]!=0).any()`而非`not isna().all()`，因为0值不是NaN但也不应使用
- 不同公司的利息支出字段不同：茅台用`interest_expenses`，五粮液用`benefit_finance_fee`，需优先级合并

## 银行股数据特性（v3.1.2审计）
- 银行API返回字段值可能为空字符串`''`（非0），data_provider转换后为0
- `operating_costs`/`total_current_assets`/`current_total_debt`/`sale_received_cash`：银行股这4个字段全为空字符串
- 银行毛利率应为0（oper_cost=0时不再误算为100%），收现比/流动比率也为0
- 一票否决D/E>3.0会正确否决银行股，这是预期行为

## 性能基准（v3.1.2优化后）
- Calculator单次：48ms（原239ms，5x提速，预建索引+numpy数组替代iterrows）
- 评分全链路：55ms/只
- 4000只from-db评分：预估3.7分钟

## 数据完整度功能（v3.1.3新增）
- calculator.py新增`get_completeness_info()`方法
- Excel新增3列：数据完整度(score 0-100)、季度覆盖(如4/4或3/4 缺24Q2)、缺失字段(如无或营收,OCF)
- 评分逻辑：季度覆盖率60%权重 + 关键字段质量40%权重
- 关键字段6项：营收/归母净利/OCF/总资产/归母权益/股东权益
- 缺失判定：最近4季度全为NaN才算缺失（0是合法值如银行股）
- 条件格式：完整度<60红色、<80黄色；季度覆盖有缺黄色；字段有缺黄色
