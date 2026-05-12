# CDP Bridge SOP

## 用途
Chrome DevTools Protocol 直连 driver，作为 TMWebDriver 不可用时的回退方案。
提供 web_scan() 和 web_execute_js() 的底层实现。

## 文件
- `cdp_bridge.py` — CDPDriver + CDPSession 类
- 依赖: `websocket-client` (pip install websocket-client)

## 快速使用
```python
from cdp_bridge import CDPDriver
driver = CDPDriver(port=9222)
result = driver.execute_js("document.title")  # {"data": "页面标题"}
html = driver.get_main_block()  # 简化 HTML
```

## 关键行为
- 返回值: execute_js → `{"data": result, "error": str?}`
- web_scan 返回键: `{"content": html}`（不是 data）
- web_execute_js 返回键: `{"js_return": result}`（不是 data）
- 隐身模式: `--window-position=-32000,-32000` 离屏窗口
- 默认端口: 9222

## 顶层 return 兼容
Runtime.evaluate 不支持顶层 return 语句。
execute_js 自动检测: 若 JS 包含 return 且以 function/var/let/const 开头，
则将最后一个 `return <expr>;` 替换为 `<expr>` 作为求值表达式。

## 常见坑
- 返回值键名不是 data，是 content（scan）和 js_return（execute_js）
- Chrome 需以 `--remote-debugging-port=9222` 启动
- ga.py 已处理 TMWebDriver → CDP 回退，无需手动切换
- 不要用 --incognito（扩展不注入 content script）