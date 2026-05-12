# 2026-04-27 工作日志

## 数据源修复与备用源添加

### 问题
东方财富 `stock_individual_info_em` 和 `stock_zh_a_spot_em` 接口持续被拒绝（RemoteDisconnected），导致股票名称、行业、总市值、PE-TTM 全部获取失败。

### 修复内容
1. **westock-data profile 解析 bug 修复**：`lines[1]` 是 Markdown 分隔符行（`| --- | --- |`），应取 `lines[2]` 作为数据行
2. **subprocess Windows 兼容修复**：PowerShell 下调用 npx 需要 `shell=True`
3. **添加 westock-data 备用源**：股票名称、行业通过 `westock-data profile` 获取
4. **添加 NeoData 备用源**：总市值、PE-TTM 通过 NeoData 金融数据搜索获取
5. **NeoData 脚本路径**：`~/.workbuddy/plugins/marketplaces/cb_teams_marketplace/plugins/finance-data/skills/neodata-financial-search/scripts/query.py`

### 验证结果（全部通过）
| 字段 | 600519 贵州茅台 | 000858 五粮液 |
|------|----------------|--------------|
| 名称 | 贵州茅台 ✅ | 五粮液 ✅ |
| 行业 | 食品饮料 ✅ | 食品饮料 ✅ |
| 总市值 | 17,571.86亿 ✅ | 3,889.37亿 ✅ |
| PE-TTM | 21.24 ✅ | 13.68 ✅ |

### 评分验证
- 贵州茅台：总分 62.08（成长1.33/盈利100/现金流98.32/偿债80.56/估值0）
- 五粮液：总分 63.56（成长0/盈利100/现金流100/偿债69.36/估值31.6）
- 五粮液营收同比 -52.66%、净利润同比 -65.62% 为真实数据（2025三季报）

### 文件变更
- `data_provider.py`：添加 `_neodata_query()`、修复 `_westock_profile()` 解析、重写 `get_stock_quote()` 添加 NeoData 备用
- `README.md`：更新数据源优先级表、断点续传说明、更新日志

### 待完成
- 全量 139 只股票 fetch-only + from-db 评分测试（stock_pool.txt 只有 139 只，非 4500+）
- 注意：`--pool` 参数需要使用绝对路径，否则 `load_stock_pool` 找不到文件
