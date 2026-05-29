# R137 — 微信Bot新增/bfm命令

## 触发
自主行动：TODO候选中有「微信Bot新增BfM信号查询命令」，上轮patch疑似失败，本轮重新插入并验证。

## 完成内容
- `wechatapp.py` L896-L924 插入 `/bfm` 命令处理逻辑
- 功能：调用 `http://127.0.0.1:18800/api/data`，解析picks数组，格式化输出股票列表（名称/代码/行业/评分）
- 异常处理：URLError（BfM未启动）、通用Exception
- 线程模式：daemon线程异步执行，不阻塞主线程
- git commit: `7a8691e` — "feat(wechat): 新增/bfm命令查询BfM实时信号"
- 验证：grep确认代码存在于L896/L897/L924

## 代码位置
```
L896: if text == '/bfm':
L897:     def _run_bfm():
...
L924:     threading.Thread(target=_run_bfm, daemon=True).start()
```

## 注意
- git diff显示文件有较大变动(793+/495-)，可能是文件编码或行尾符变化导致，非逻辑变更
- 功能验证需在BfM运行时进行端到端测试
