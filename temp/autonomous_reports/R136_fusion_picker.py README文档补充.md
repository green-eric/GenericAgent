# R136 — fusion_picker.py README文档补充

## 触发
用户提问："ScoreSys+BfM 动态权重融合选股工具 有文档没"

## 完成内容
- `README.md` 新增 **6.3节**「ScoreSys+BfM动态权重融合选股 — fusion_picker.py」
- 正文从 ~1262行扩展到 ~1309行（净增428行，含替换40行）
- 目录同步添加 `6.3 ScoreSys+BfM 动态权重融合选股 (fusion_picker.py)`
- git commit: `2c35a44` — "docs: fusion_picker.py完整使用文档(6.3节) + README目录更新"

## 文档覆盖内容
1. 动态权重策略表（牛市30/70、熊市70/30、震荡市50/50）
2. BfM代理评分5维说明（资金/业绩/稳定性/动量/行业动量）
3. 命令行参数完整参考（--db/--top/--regime/--weights/--json/--export）
4. 输出格式示例（表格 + JSON）
5. regime自动推断逻辑（从scores表众数）
6. 与BfM实时信号的关系说明（离线 vs 在线互补）

## 回归验证
- `python fusion_picker.py --help` 正常输出
- README目录锚点与正文章节号一致
