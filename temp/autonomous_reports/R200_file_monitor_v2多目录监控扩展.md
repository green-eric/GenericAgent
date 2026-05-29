# file_monitor_v2 多目录监控扩展报告

> 任务: 扩展file_monitor_v2支持同时监控多个目录(ScoreSys/BfM/GA)，统一事件总线
> 完成时间: 2026-05-19

## 实现方案

### 新增 MultiDirMonitor 类
- **多目录独立监控**: 每个目录独立线程 + 独立回调链
- **统一事件总线**: 全局回调(`on_any`)接收所有目录事件
- **事件来源标识**: 每个事件带 `dir_tag` 属性标识来源目录
- **命令行支持**: `--multi tag1=path1 tag2=path2 ...` 模式

### API
```python
m = MultiDirMonitor(interval=2.0)
m.add_watch("scoresys", "/path/to/scoresys/data", callbacks=[...])
m.add_watch("bfm", "/path/to/bfm/data", callbacks=[...])
m.add_watch("ga", "/path/to/ga/config", callbacks=[...])
m.on_any(lambda e: print(f"[{e.dir_tag}] {e.event_type}: {e.src_path}"))
m.start()
```

### 验证结果

#### 单元测试 (6/6 通过)
- ✅ Syntax OK
- ✅ Import OK (FileMonitor, ScoreSysTrigger, MultiDirMonitor, FileEvent)
- ✅ add_watch 3 watchers
- ✅ _snap 文件快照
- ✅ _events 事件检测 (created/modified/deleted)
- ✅ dir_tag 属性

#### E2E Demo (5/5 事件全部捕获)
| 事件 | 目录 | 结果 |
|------|------|------|
| created | scoresys | ✅ |
| created | bfm | ✅ |
| created | ga | ✅ |
| modified | scoresys | ✅ |
| deleted | bfm | ✅ |

```
Created: 3/3  Modified: 1/1  Deleted: 1/1
🎉 E2E Demo PASSED — 3-dir monitoring works!
```

## 代码变更
- 文件: `./file_monitor_v2.py`
- 新增: `MultiDirMonitor` 类 (~100行)
- 新增: `__main__` 的 `--multi` 命令行模式
- 未修改: `FileMonitor`, `ScoreSysTrigger` (向后兼容)

## 验收
✅ 3目录同时监控 Demo 通过
