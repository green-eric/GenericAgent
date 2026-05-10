# GA TODO

## 待优化
- [ ] 回复速度: agent轮次多(可达10+轮)，需减少搜索/工具调用次数，目标<3秒回复
- [ ] 格式自适应: 电脑端(富文本/表格/K线图) vs 手机端(简洁排版/短段落/emoji分段)
- [ ] C盘空间: 仅剩21.1GB (90%)，需清理

## 已完成 (2026-05-10)
- [x] 移除 wechatapp.py 中残留的 import webbrowser
- [x] 清理 temp 临时文件 (5个 .ai.py + __pycache__)
- [x] 轮转 wechatapp.log (293KB → bak)
- [x] 创建 TODO.md
- [x] web_search 修复: 默认引擎改为 duckduckgo, Google JS重定向自动fallback
