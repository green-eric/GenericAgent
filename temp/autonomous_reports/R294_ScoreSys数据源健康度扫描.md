# R295 | ScoreSys 数据源健康度扫描报告

## 扫描时间
2026-05-28 14:xx (自主行动)

## 数据源状态总览

| 数据源 | 用途 | 直连 | 代理 | 延迟 | 状态 |
|--------|------|------|------|------|------|
| 腾讯行情(qt.gtimg.cn) | 实时/历史行情 | ✅ | ✅ | 0.07-0.13s | 🟢 健康 |
| 新浪行业页面 | 行业分类 | ✅ | - | 0.36s | 🟢 健康 |
| 东方财富API | 行情数据 | ✅ | - | 0.31s | 🟢 健康 |
| Tushare API | 财务数据 | ✅ | - | 0.10s | 🟢 健康 |
| AkShare | 财务/行业 | ❌ | ❌ | - | 🔴 双失败 |
| ScoreSys DB | 本地缓存 | ✅ | - | - | 🟢 1.5GB |
| BfM DB | 本地缓存 | ❌ | - | - | 🟡 不存在 |

## 详细发现

### 1. 腾讯行情 (qt.gtimg.cn) ✅
- 直连延迟: 0.07-0.13s
- 代理延迟: 0.12s
- 数据格式正常，返回完整
- ScoreSys 6个模块均使用: backfill_quotes_incremental, data_provider, evaluator, fetcher, fill_valuation, _verify_api_db

### 2. 新浪行业页面 ✅
- 直连延迟: 0.36s
- 用于行业分类数据

### 3. 东方财富 API ✅
- 直连延迟: 0.31s
- AkShare 底层依赖 eastmoney，但 AkShare 封装层在直连/代理下均失败
- 东方财富 API 本身可达，问题在 AkShare 封装层

### 4. Tushare API ✅
- 直连延迟: 0.10s
- API 端点可达

### 5. AkShare 🔴
- 直连: RemoteDisconnected
- 代理(7897): Max retries exceeded
- 根因: AkShare 使用 eastmoney HTTPS API，当前网络环境下连接被远端关闭
- **影响**: 财务数据、行业数据无法通过 AkShare 获取
- **降级方案**: ScoreSys 主要依赖腾讯行情+新浪，AkShare 用于财务数据回填。DB 中 financials 表最新数据 2026-03-31，距今约2个月未更新

### 6. ScoreSys DB ✅
- 大小: 1.5GB
- 表: financials(192K行), quotes(3.2M行, 最新2026-05-28), stocks(4344行), scores(52K行, 最新2026-05-28)
- 行情数据实时，财务数据略有滞后

### 7. BfM DB 🟡
- stock_data.db 不存在于 BfM 目录
- BfM 可能使用 ScoreSys 的 DB 或独立配置

## 风险评估

| 风险项 | 级别 | 说明 |
|--------|------|------|
| AkShare 不可用 | 中 | 财务数据无法自动回填，DB 中财务数据滞后2个月 |
| BfM DB 缺失 | 低 | 可能不影响运行，需确认 BfM 数据源配置 |
| 代理 7897 | 高 | clash-verge 持续离线(R291)，代理不可用 |

## 建议
1. **P0**: 恢复 clash-verge 代理 — AkShare 在代理下可能恢复（R291已诊断）
2. **P1**: 将数据源健康检查集成到 daily_health_check.py — 监控腾讯/AkShare 可用性
3. **P2**: 考虑财务数据替代数据源（Tushare 可达）

## 记忆更新建议
- L2: AkShare 当前双失败(直连+代理), eastmoney API 本身可达, 问题在 AkShare 封装层
- L2: ScoreSys DB 表结构: quotes(3.2M行), financials(192K行), scores(52K行)
