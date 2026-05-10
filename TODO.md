# GA TODO

## 待执行

- [ ] **momentum 震荡市负IC修复** [P1]: R65/R83已确认momentum在RANGE regime下IC=-0.1139完全失效，需修改scorer.py中momentum的regime自适应逻辑（震荡市降权/反转信号），实测验证IC改善
- [ ] **ScoreSys因子改造实测** [P0]: R76方案已定（momentum regime-specific + cashflow增强 + profitability反转），但未实测。需跑回测对比改造前后IC/夏普，目标avgIC>0.055
- [ ] **格式自适应方案A** [P2]: 已检测终端宽度，需改agent_loop.py加source参数区分微信/电脑端调用来源，实现自动格式切换
- [x] **temp/目录瘦身** [P2]: 235.8MB→144.7MB，释放91.1MB。model_responses保留30个，chrome缓存已清理
- [x] **usage_log.jsonl轮转** [P3]: 200.9KB→64.3KB，归档1064行到.bak，保留最近500行
- [x] **autonomous_reports去重** [P3]: 76→72，删除R25/R80重复规划报告
- [ ] **格式自适应方案A** [P2]: ⚠️ 需请示用户。已读完agent_loop.py(127行)，需改核心代码加source参数

## 已完成 (2026-05-11)
- [x] 回复速度优化: file_read默认show_linenos=False、精简工具输出、减少verbose yield、压缩file_read参数显示
- [x] 格式自适应检测: 终端宽度80列=电脑端，微信/手机端<60列需简洁排版
- [x] C盘空间清理: 38.9GB可用(19%)，DISM需管理员权限暂缓
- [x] ScoreSys V13.5因子改造实测: momentum/cashflow/profitability三方向改造完成
- [x] BfM SSE多客户端并发验证
- [x] K线图数据源修复: 东方财富API被墙→改腾讯API