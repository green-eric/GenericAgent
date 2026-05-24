# Mini-SOP 1: 环境扫描模式

## 触发
自主行动或用户要求了解环境状态时

## 流程
1. **选扫描类型** — Python包 / 端口服务 / 目录结构 / CLI工具
2. **执行扫描** — 
   - 包: `pip list` + `importlib.metadata` 查版本
   - 端口: `socket.connect_ex()` 批量探测常见端口
   - 目录: `os.walk()` 2层深度 + 按大小/扩展名分类
   - CLI: `shutil.which()` 批量检测
3. **过滤记录** — 对比 `global_mem.txt`，标记"已记录"vs"新发现"
4. **写入报告** — `./autonomous_reports/R{n}_XXX.md`
5. **更新记忆** — 新工具写入 `global_mem.txt` L2

## 输出格式
`## 摘要` → `## 发现的工具/服务` → `## 建议`
每个发现项: 名称 | 版本 | 用途 | 用法要点 | 记忆状态
