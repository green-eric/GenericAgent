# R237 | 定时任务max_delay优化 | 2026-05-22

## 执行摘要
将3个定时任务的max_delay_hours从4h调整为8h，解决下午开机全部跳过的问题。

---

## 修改内容

| 任务 | schedule | repeat | 修改前 | 修改后 | 效果 |
|------|----------|--------|--------|--------|------|
| daily_backtest | 07:30 | daily | 4h (11:30截止) | 8h (15:30截止) | 下午3:30前开机可触发 |
| scoresys_check_score_done | 09:00 | every_30m | 4h (13:00截止) | 8h (17:00截止) | 下午5:00前开机可触发 |
| scoresys_daily_backtest | 15:30 | weekday | 4h (19:30截止) | 8h (23:30截止) | 晚上11:30前开机可触发 |

---

## 根因分析
scheduler.py中max_delay_hours检查逻辑：
```python
if (now_minutes - sched_minutes) > max_delay * 60:
    SKIP  # 超过max_delay后不再触发
```
当max_delay=4h时，如果下午开机（如15:00），07:30的任务已超时7.5h，全部被跳过。

---

## 验证
- ✅ 3个JSON文件已更新
- ✅ JSON格式验证通过
- ⚠️ scheduler.py需重启才能生效（当前scheduler未运行，下次启动自动生效）

---

*自动生成 @ 2026-05-22*
