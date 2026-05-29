# R242 | LM Studio本地LLM测试 | 2026-05-22

## 完成内容

### 1. Runtime 安装
- 安装 `llama.cpp-win-x86_64-avx2@2.14.0`
- 已选中为默认 GGUF 推理引擎

### 2. 模型下载
- 下载 `qwen2.5-0.5b-instruct` (Q4_K_M, 379MB)
- 来源: HF镜像 (hf-mirror.com)，原始HF连不上
- 原模型 `gemma-4-e2b` (3.19GB) 因 RAM 不足(15.7GB)加载超时，已替换

### 3. 推理测试 (HTTP API: localhost:1234)

| 测试项 | 延迟 | 结果 |
|--------|------|------|
| 中文Q&A | 5.9s | 正常回复自我介绍 |
| 代码生成(快排) | 5.9s | 正确输出Python代码 |
| 多轮对话 | 2.4s | 3+3=6 正确 |

**全部通过 ✅**

### 注意事项
- `lms load` CLI 命令会超时（已知问题），但 HTTP API 可直接推理
- LM Studio server 需在 port 1234 运行
- 推理走 CPU 模式（Intel Iris Xe，无 CUDA）

*自动生成 @ 2026-05-22*
