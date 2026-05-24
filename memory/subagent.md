# Subagent 调用 SOP

## 文件IO协议

- 目录：`temp/{task_name}/`（cwd在temp/时即`./{task_name}/`）
- 启动：`python agentmain.py --task {name} [--input "短文本"] [--llm_no N]`（cwd=代码根）
- `--input`自动建目录+清旧output+写input.txt；长文本先手动写input.txt再启动(不带--input)
- 自动后台启动，print PID then exit
- subagent的cwd还是temp，不是task目录
- input：目标+约束即可，subagent同等智能。**禁写步骤/过度描述**，大量数据给路径
- 可选fork功能（继承对话上下文）: code_run(inline_eval=True)，将变量history（自动注入,str）写入task目录下_history.json
- 通信：output.txt(append,`[ROUND END]`=轮完成) → 写reply.txt继续 → 不写10min退出。reply后输出为output1/2/3.txt(同格式)
- 干预文件：`_stop`(当轮结束退出) | `_keyinfo`(注入working memory) | `_intervene`(追加指令)
- 监察模式：**主agent空闲时应读output观察进度，必要时用干预文件纠偏，禁止无脑长时间sleep**
- 若加`--verbose`，output将包含工具执行结果，主agent可直接审查原始数据而非仅信任摘要

## 场景1：测试模式 - 行为验证
**用途**：观察agent真实行为，修正RULES/L2/L3/SOP
**流程**：创建test_path/写input.txt→启动subagent→轮询output.txt(2秒间隔)→验证→清理重复
**测试原则**：只给目标，不提示位置/不诱导做法，观察自主选择
**修正闭环**：发现问题→设计测试→定位根源(RULES/L2/L3/SOP)→patch修正→验证
**技术要点**：Insight优先级>SOP；subagent的cwd=temp/
**两种测试**：
- 测SOP质量：input指定SOP名（如"用ezgmail_sop查看最近3封未读邮件"），排除导航干扰，失败即SOP问题
- 测导航能力：input只写目标，验证subagent能自主从insight找到正确SOP。禁止内联SOP内容

## 场景2：Map模式 - 并行处理
**用途**：将N个独立同构子任务分发给各自的subagent处理
**核心优势**：独立上下文。避免处理文档A的长上下文污染处理文档B的质量
**约束**：
- 文件系统共享是优点：不同agent处理不同输入文件，产生不同输出文件
- 共享资源冲突：键鼠不可共享；浏览器暂时不可并行使用，避免同时操作同一标签页
- 不满足map模式的任务 → 主agent顺序执行即可，别用subagent
**标准流程（map-reduce）**：
1. 主agent准备阶段：爬取/dump数据，存为多个独立输入文件
2. 分发：对每个文件启动一个subagent处理（主agent自己也可以处理其中一个）
3. 收集：等所有subagent完成，主agent读取各输出文件，汇总结果

## subagent内部plan_mode使用
**原则**：subagent本身是完整agent，接收多步骤任务时应在内部创建plan管理执行
**触发条件**:任务包含3个以上子步骤、子步骤之间有依赖关系、需要checkpoint来恢复执行
**实现方式**：
1. **主agent创建subagent时**：在input.txt中说明任务包含多个步骤，建议使用plan_mode
2. **subagent内部执行**：检测到多步骤任务后，创建 `./subagent_plan.md` 并使用plan_mode执行
3. **主agent监控**：只关注最终结果（output*.txt），不需要关心subagent内部如何执行
4. **文件传递机制**：主agent创建subagent时在task_dir中生成 `context.json`，包含所有文件的**绝对路径**
   **⚠ subagent启动后第一步必须读取context.json**
   **⚠ 所有文件操作必须使用context.json中的绝对路径**
**格式示例**：
```json
{
  "task": "任务描述",
  "work_dir": "/absolute/path/to/plan_dir/",
  "input_files": {
    "paper_info": "/absolute/path/to/paper_info.txt"
  },
  "output_files": {
    "pdf": "/absolute/path/to/paper.pdf",
    "report": "/absolute/path/to/paper_report.md"
  },
  "dependencies": ["paper_info.txt必须存在"]
}
```

## 场景3：调度模式 - 主agent主动分发

### 调度决策框架

**何时用 subagent**：
- 任务可独立执行（不依赖主agent的上下文状态）
- 任务耗时 > 30s（避免主agent阻塞）
- 需要隔离上下文（避免长上下文污染主agent）
- 可并行（多个独立子任务）

**何时不用 subagent**：
- 任务依赖主agent的实时交互（如浏览器操作）
- 任务简单（< 10s 可完成）
- 需要共享键鼠/浏览器状态
- 任务间有强依赖（需顺序执行）

### Input 构造模式

| 场景 | input 内容 | 示例 |
|------|-----------|------|
| 简单任务 | 目标 + 约束 | `"扫描D:/Project下所有项目的CHANGELOG完整性"` |
| 复杂任务 | 目标 + 输入文件路径 + 输出期望 | `"分析 ./data/report.pdf，提取关键数据，结果写入 ./output/summary.md"` |
| Map模式 | 每个subagent处理一个分片 | `"处理 ./data/chunk_001.csv，结果写入 ./output/result_001.json"` |
| 测试模式 | 仅目标，不提示位置 | `"用 vision_sop 查看最近截图内容"` |

**Input 构造原则**：
- ✅ 给目标 + 约束 + 文件路径
- ✅ 大量数据给文件路径，不内联
- ✅ 多步骤任务建议 plan_mode
- ❌ 不写具体步骤（subagent 同等智能）
- ❌ 不内联 SOP 内容（让 subagent 自己查）
- ❌ 不过度描述（input 越长，subagent 理解负担越大）

### 结果解析

**正常完成**：
1. 读取 `output.txt`（或 `output1/2/3.txt`）
2. 检查最后一行是否包含 `[ROUND END]`
3. 提取关键结论（忽略工具调用过程）
4. 验证输出文件是否存在（如 task_dir 中的报告文件）

**结果验证清单**：
- [ ] output.txt 存在且非空
- [ ] 包含 `[ROUND END]` 标记
- [ ] 输出文件（如报告）存在
- [ ] 结果与预期一致（如数据量、格式）

### 错误处理

| 错误类型 | 症状 | 处理方式 |
|---------|------|---------|
| 启动失败 | 进程立即退出，无 output.txt | 检查 task_dir/input.txt 是否存在；重试一次 |
| 超时未完成 | output.txt 存在但无 `[ROUND END]` | 写 `_intervene` 追加指令；或写 `_stop` 终止后主agent接管 |
| 输出为空 | output.txt 存在但内容极少 | 检查 input 是否过于模糊；重新构造 input 后重试 |
| 工具调用失败 | output 中大量 Error/Traceback | 写 `_keyinfo` 注入关键上下文；或主agent直接处理 |
| 无限循环 | output 持续增长但无进展 | 写 `_stop` 立即终止；分析 input 是否导致歧义 |
| 资源冲突 | 多个subagent操作同一文件 | 确保每个subagent有独立 task_dir；共享资源只读 |

**干预文件使用**：
```
echo "补充指令" > temp/{task_name}/_intervene    # 追加指令
echo "关键信息" > temp/{task_name}/_keyinfo      # 注入working memory
echo "" > temp/{task_name}/_stop                 # 当轮结束后退出
```

**重试策略**：
1. 首次失败 → 检查 output 末尾，分析原因
2. 二次失败 → 修改 input（更明确的目标/约束），重新启动
3. 三次失败 → 主agent 直接执行，记录 subagent 失败原因到报告