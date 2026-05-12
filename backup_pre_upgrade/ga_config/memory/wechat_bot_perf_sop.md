# 微信 Bot 性能优化 SOP

## 关键参数（勿随意改动）

| 参数 | 文件 | 当前值 | 说明 |
|------|------|--------|------|
| context_win | llmcore.py:527 | 60000 | 上下文窗口，阈值=context_win*3=180K。之前28K太小导致频繁裁剪 |
| max_len | llmcore.py:33 | 2000 | compress_history_tags 压缩阈值。之前800太激进 |
| tool_result截断 | agent_loop.py:91, llmcore.py:994 | 3000字符 | 网页搜索结果等长内容截断后存入history |
| timeout | wechatapp.py | 120s | 消息队列get超时。之前30s在多轮tool_use时会超时 |
| compress执行频率 | llmcore.py:33 | 每次 | 之前每5次才执行一次，改为每次调用都压缩 |

## 典型坑

1. context_win 不能太小：多轮 tool_use（网页搜索+解析）一轮就能产生几千字符的 tool_result，28K 阈值 84K 三四轮就爆
2. tool_result 是膨胀主因：网页搜索结果动辄 5K-10K 字符，必须截断到 3K 以内
3. compress_history_tags 计数器：之前用 _cd % 5 每5次才压缩一次，改为每次执行
4. timeout 与 tool_use 轮数相关：天气/新闻查询可能 3-5 轮 tool_use，每轮 10-20s，30s 超时不够

## 诊断方法

Get-Content "temp/wechatapp.log" -Tail 50 | Select-String "Current context"
看到 [Cut] 说明触发了裁剪，需要增大 context_win 或截断 tool_result
看到 timeout 说明需要增大 timeout 或减少 tool_use 轮数

## Git 修复记录

- 4a162f1 - fix(wechat): fmt_wx格式化+timeout120s+微信格式约束prompt
- 1974fbe - fix(llmcore): context_win 28k->60k, compress每次执行+max_len 800->2000
- 36f132e - fix(context): tool_result截断3000字符，减少history膨胀
- 6543632 - fix(wechat): Session复用+keep-alive+超时分离+连续失败重建Session
  - 根因: _post() 每次新建TCP连接，代理环境下被远端关闭 → Max retries exceeded (2199条/1.4MB日志)
  - 修复: Session连接池(pool_maxsize=10)+HTTPAdapter(max_retries=3)+keep-alive头
  - 修复: 超时分离(connect=10s, read=35s)，避免connect timeout过长
  - 修复: run_loop加连续失败计数+每5次重建Session
  - 效果: 修复后0错误(修复前0.6%错误率)，getupdates错误从2199条降为0

## 诊断方法

Get-Content "temp/wechatapp.log" -Tail 50 | Select-String "Current context"
看到 [Cut] 说明触发了裁剪，需要增大 context_win 或截断 tool_result
看到 timeout 说明需要增大 timeout 或减少 tool_use 轮数