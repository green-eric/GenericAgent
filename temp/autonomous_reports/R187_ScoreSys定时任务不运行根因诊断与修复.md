# R191 | 2026-05-18 | 诊断+修复 | ScoreSys定时任务不运行根因

## 摘要
找到并修复了ScoreSys定时任务从未成功运行的根因：config.yaml中IC数据文件使用相对路径，定时任务运行时cwd为C:\Windows\System32导致文件找不到。已修复为绝对路径，手动触发评分成功。

## 根因分析

### Bug定位过程
1. 所有定时任务LastRunTime全空（R179-R190多次确认）
2. 手动运行 `main.py --from-db --all --save-db` 报错：`FileNotFoundError: data/ic_data/regime_ic.json`
3. 文件实际存在于 `D:\Project\ScoreSys\data\ic_data\regime_ic.json` (3323 bytes)
4. `weight_optimizer.py` 中 `IC_DATA_FILE` 优先使用 `config._get('ic_data', 'file', None)` 的返回值
5. config.yaml中配置为相对路径 `data/ic_data/regime_ic.json`
6. 定时任务启动时cwd通常为 `C:\Windows\System32`，相对路径解析为 `C:\Windows\System32\data\ic_data\regime_ic.json` → 不存在！

### 修复内容
```yaml
# 修复前 (config.yaml L91)
ic_data:
  file: data/ic_data/regime_ic.json

# 修复后
ic_data:
  file: D:/Project/ScoreSys/data/ic_data/regime_ic.json
```

## 验证结果
- ✅ 手动触发评分成功：4344条结果，耗时74秒
- ✅ xlsx已生成：`评分结果_20260518_151559.xlsx` (1018960 bytes)
- ⚠️ scores表日期仍为2026-05-15（数据库最新行情数据为5/15，今天5/18的行情未入库）

## 遗留问题
- scores表需要等明天(5/19)新交易日数据入库后才会产生新日期记录
- 定时任务是否从明天起正常运行，需观察
- `ScoreSys_DailyScore_New` 任务使用 `python` 而非完整路径 `C:\Python312\python.exe`，可能也有路径问题

## 记忆更新
- config.yaml中所有相对路径在定时任务场景下都会失效，建议全面检查
- weight_optimizer.py的IC_DATA_FILE解析逻辑：config返回非None时直接使用（不拼接_base_dir）
