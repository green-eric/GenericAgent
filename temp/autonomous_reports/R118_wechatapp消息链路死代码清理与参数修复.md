# R118 | 2026-05-14 | 修复 | wechatapp.py 消息链路死代码清理与参数修复

## 问题根因（3个叠加bug）

### Bug 1: text 提取路径错误（L586）
```python
# 错误
text += item.get('text', '')
# 正确
text += item.get('text_item', {}).get('text', '')
```
API 返回结构是 `item.text_item.text`，不是 `item.text`。导致 text 永远为空，L590 `if not text and not media: continue` 直接跳过所有消息。

### Bug 2: 参数不匹配（L601）
```python
# 错误
on_message(self, msg)     # 传2参，且 on_message 是模块级死代码
# 正确
on_message(self, uid, text, ctx, media)  # 传5参，匹配 _on_message 签名
```
`run_loop` 调用的是 `on_message(self, msg)`，但实际处理函数 `_on_message` 需要 `(bot, uid, text, ctx, media)` 5个参数。模块级 `on_message` 成了死代码。

### Bug 3: 158行模块级死代码（L695-L849）
- 模块级 `on_message(bot, msg)` 定义后从未被调用
- 内部引用未定义函数：`_dl_media()` → NameError
- 两套并行处理逻辑互相冲突

## 修复内容

| # | 操作 | 位置 |
|---|------|------|
| 1 | 修复 text 提取路径 | L586 |
| 2 | 修复调用参数 `(self, uid, text, ctx, media)` | L695 |
| 3 | 删除模块级 `on_message` 死代码（155行） | L695-L849 |
| 4 | 删除 `_progress_hint` 死代码（3行） | L691-L693 |

文件从 996 行精简到 837 行，语法检查通过。

## 当前消息链路（单一清晰路径）

```
get_updates API
  → parse messages (text_item.text + media)
  → on_message(bot, uid, text, ctx, media)  [run_loop L601]
    → _on_message(bot, uid, text, ctx, media)  [main() L746]
      → 命令处理 (/help /pc /mobile)
      → K线图生成 (6位代码)
      → GeneraticAgent().run(text) → 回复用户
```

## 验收标准
- [ ] 重启 wechatapp.py 后，发送普通文本消息，收到 Agent 回复
- [ ] 发送 /help 命令，收到帮助信息
- [ ] 发送 6位股票代码，收到 K线图+评分

## 注意事项
- 修复后需重启 wechatapp.py 才能生效
- 如果仍不回复，检查 GeneraticAgent 是否正常初始化
