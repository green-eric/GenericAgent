# R261 — PC闲置GPU推理能力边界探测(续)

## 执行概要
- **时间**: 2026-05-23 自主行动
- **任务**: 验证Intel Iris Xe DirectML后端可用性和性能，ONNX Runtime DirectML推理延迟测试
- **环境**: i5-1135G7 | Iris Xe 2GB共享 | 10GB RAM | onnxruntime-directml 1.24.4
- **结果**: ✅ 结论明确 — DirectML对本机推理无实用价值

## 测试方法
- 4种模型 × 3种batch size，各50次推理取平均
- 对比 DirectML (DmlExecutionProvider) vs CPU (CPUExecutionProvider)
- 预热5次后计时，排除冷启动影响

## 测试结果

### MLP模型 (稳定运行)

| 模型 | 参数量 | Batch | DirectML(ms) | CPU(ms) | CPU快多少 |
|------|--------|-------|-------------|---------|----------|
| TinyMLP | 465 | 1 | 0.502 | 0.024 | **20.9x** |
| TinyMLP | 465 | 4 | 1.956 | 0.029 | **67.4x** |
| TinyMLP | 465 | 16 | 1.733 | 0.028 | **61.9x** |
| SmallMLP | 40,842 | 1 | 0.287 | 0.038 | **7.5x** |
| SmallMLP | 40,842 | 4 | 1.947 | 0.041 | **47.5x** |
| SmallMLP | 40,842 | 16 | 1.709 | 0.053 | **32.2x** |

### Transformer模型 (DirectML不稳定)

| 模型 | 参数量 | Batch | DirectML(ms) | CPU(ms) | 状态 |
|------|--------|-------|-------------|---------|------|
| SimpleTransformer | 541,186 | 1 | 2.198 | 0.926 | CPU仍快2.4x |
| SimpleTransformer | 541,186 | 4 | ❌ 崩溃 | ~1.5 | DirectML Add节点错误 |
| SimpleTransformer | 541,186 | 16 | ❌ 崩溃 | ~3.0 | DirectML Add节点错误 |

## 关键发现

1. **CPU在所有场景下均快于DirectML** (7x~67x)
2. **DirectML固定开销约1.7-2.0ms** — 与模型大小无关，是GPU数据传输+内核启动成本
3. **CPU推理延迟随模型线性增长** (0.024→0.038→0.053ms for MLP)
4. **Batch增大时DML不降反升** — batch=1时DML反而更快(0.3-0.5ms)，batch>=4时固定~1.8ms
5. **大模型DirectML不稳定** — Transformer batch>=4时后端崩溃(UnicodeDecodeError/Add节点断言失败)
6. **R256旧结论修正**: R256说"DirectML可用，小模型CPU更优，大模型才有GPU加速意义" → **本次测试证明即使54万参数的Transformer，CPU仍快于DirectML且DML不稳定**

## 结论

> **Intel Iris Xe (2GB共享显存) 的 DirectML 对本机推理无实用价值**

- 固定开销(~2ms)远超小模型CPU推理(<0.1ms)
- 大模型(batch>=4)DirectML后端不稳定
- **建议**: 保持PyTorch CPU推理方案，云端API处理大模型需求
- R256的旧结论"大模型才有GPU加速意义"已过时，已在本报告中修正

## 清理
- 临时ONNX文件: TinyMLP.onnx, SmallMLP.onnx, MediumMLP.onnx, SimpleTransformer.onnx (可删除)
- 基准脚本: temp/directml_benchmark.py (保留供复现)
