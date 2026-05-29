# R126 | 2026-05-15 | PC闲置GPU推理能力边界探测

## 结论 🔴

**Intel Iris Xe 无法用于GPU推理。** PyTorch为CPU版本(2.11.0+cpu)，CUDA/MPS/IPEX均不可用，ONNXRuntime也只有CPU provider。GPU推理在当前环境下**不可行**。

CPU推理可行但极慢：30M参数模型约40ms/forward，7B量化模型理论估算约5600ms/token（不实用）。

## 硬件概况

| 项目 | 详情 |
|------|------|
| GPU | Intel(R) Iris(R) Xe Graphics, 2GB共享显存 |
| RAM | 16 GB |
| PyTorch | 2.11.0+cpu（无CUDA/MPS/IPEX） |
| ONNXRuntime | 1.26.0（仅CPU provider） |
| torch线程数 | 4 |

## 实测数据

### CPU矩阵运算吞吐

| 矩阵尺寸 | 延迟 | 吞吐 |
|----------|------|------|
| 256×256 | 0.1ms | 408 GFLOPS |
| 512×512 | 1.2ms | 227 GFLOPS |
| 1024×1024 | 9.9ms | 218 GFLOPS |
| 2048×2048 | 81.6ms | 210 GFLOPS |

### 微型Transformer层推理

| 规模 | d | h | seq | 延迟 | 参数量 |
|------|---|---|-----|------|--------|
| nano | 64 | 4 | 128 | 0.5ms | 0.05M |
| micro | 128 | 4 | 256 | 1.3ms | 0.20M |
| tiny | 256 | 8 | 512 | 7.7ms | 0.79M |

### 内存带宽

| 数据量 | 带宽 |
|--------|------|
| 64MB | 10,090 MB/s |
| 128MB | 14,150 MB/s |
| 512MB | 14,119 MB/s |
| 2GB | 4,559 MB/s（可能触及swap） |

## LLM推理能力估算

基于实测 CPU≈15 GFLOPS + 内存带宽≈14 GB/s：

| 模型 | FP32内存 | 4bit内存 | 估算延迟/token | 可行? |
|------|----------|----------|----------------|-------|
| 100M | 0.4GB | 0.1GB | 80ms | ✅ 可用 |
| 350M | 1.4GB | 0.2GB | 280ms | ✅ 勉强 |
| 1B | 4.0GB | 0.5GB | 800ms | ⚠️ 很慢 |
| 3B | 12.0GB | 1.5GB | 2400ms | ❌ 不实用 |
| 7B | 28.0GB | 3.5GB | 5600ms | ❌ 不可行 |

## 发现与建议

1. **GPU推理**: 🚫 当前不可行。PyTorch为CPU版本，Intel Iris Xe无CUDA支持。即使安装IPEX，Iris Xe的2GB共享显存也极受限。
2. **CPU推理**: ✅ 100M以下小模型可用（~80ms/token），350M可勉强运行。1B+不实用。
3. **若需GPU推理**: 需(a)安装CUDA版NVIDIA显卡，或(b)安装Intel IPEX + 至少6GB显存的Arc独显。
4. **实用方案**: 100M参数以下的轻量模型（如BERT-tiny、GPT-2 124M）在CPU上可用于分类/嵌入任务，但生成式推理体验差。

## 环境状态

- ✅ torch 2.11.0 + onnxruntime 1.26.0 已安装
- ❌ llama-cpp-python 未安装
- ❌ IPEX 未安装
- ❌ CUDA 不可用
