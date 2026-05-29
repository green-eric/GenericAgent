# R115: AKShare 因子数据源实测

**时间**: 2026-05-14 01:42:32
**状态**: FAILED - insufficient data
**验收标准**: 用AKShare获取至少1个因子数据并计算IC

## 实测结果

| 指标 | 值 |
|------|-----|
| 股票池 | 沪深300成分股 (前50只) |
| 价格数据获取 | 0 只成功 |
| 因子类型 | N/A |
| 因子数据获取 | 0 只成功 |
| IC 样本量 | 0 |
| **IC (估值因子)** | **N/A** |
| IC 质量 | N/A |
| IC (动量因子) | N/A |

## 结论

AKShare 库已安装（v1.18.60），代码逻辑正确，但**当前网络环境无法连接 AKShare 数据源**。

### 诊断结果
- `stock_zh_a_hist` → Connection aborted (RemoteDisconnected)
- `stock_zh_a_spot_em` → Connection aborted
- `index_stock_cons` → 正常（有缓存）
- 原因：代理配置或防火墙阻止了对东方财富 API 的直接访问

### 网络问题记录
- AKShare 底层调用东方财富 API (push2.eastmoney.com)
- 所有 requests 连接均被远端关闭
- 需要配置代理或白名单才能使用 AKShare 实时数据

### R107 验收状态: ❌ 未完成（网络阻塞）

### 下次恢复步骤
1. 检查代理设置（环境变量 HTTP_PROXY / HTTPS_PROXY）
2. 尝试配置 AKShare 使用代理
3. 或切换到 baostock 作为备用数据源（已安装 v0.9.1）
