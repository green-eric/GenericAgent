# R66 — 微信Bot消息格式自适应

**日期**：2026-05-08  
**类型**：产出  
**状态**：✅ 完成

---

## 目标
根据发送目标（电脑端 vs 手机端）自适应调整消息格式：电脑端富文本/表格/代码块，手机端简洁排版/短段落/emoji分段。

## 探测结果

### 微信API分析
- 消息对象 `msg` 中**无** platform/device 字段
- 无法从服务端直接获取设备类型

### 消息流水线
```
on_message → sys_hint(LLM提示词) → agent推理 → _clean → _strip_md → send_text
```

## 实现方案：混合模式

| 层级 | 修改 | PC端效果 | 手机端效果 |
|------|------|----------|------------|
| 命令 | `/pc` `/mobile` `/auto` | 手动切换模式 | 手动切换模式 |
| 检测 | `_guess_device()` | 文本>150字/含代码块/表格→PC | 默认mobile |
| sys_hint | `_handle()` 分支 | 可用表格、代码块(≤15行)、详尽回复 | emoji分段、2-3行、≤500字 |
| _strip_md | `device`参数 | 代码块截断15行、保留H5-H6 | 代码块截断8行 |
| 截断 | max_len | 2800字符 | 1400字符 |

### 关键代码变更（wechatapp.py）
- `_USER_MODE = {}` — uid→模式字典
- `_guess_device(text, uid)` — 启发式检测
- `/pc` `/mobile` `/auto` 命令 — 用户手动切换
- `_strip_md(t, device='mobile')` — 设备感知格式清洗
- `_clean(t, device='mobile')` — 透传device
- `_handle()` — 设备感知sys_hint + 截断

## 验证
- ✅ 语法编译通过
- ✅ Bot重启成功（PID 3368，Kill 10旧进程）
- ⏳ 待用户端实际测试 `/pc` `/mobile` 命令

## 记忆更新建议
- 更新 global_mem.txt：添加「微信Bot支持/pc /mobile命令自适应设备格式」
