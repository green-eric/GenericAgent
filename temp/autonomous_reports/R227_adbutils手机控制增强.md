# R227 | 能力 | adbutils手机控制增强

## 结论
✅ **adb_ui_v2.py 创建完成** — 用 adbutils 替代 subprocess adb 调用，14个公开函数，API兼容原 adb_ui.py。

## 环境探测结果
| 项目 | 状态 |
|------|------|
| adbutils 包 | ✅ 已安装 (v2.12.0) |
| adb.exe (系统PATH) | ❌ 未找到 |
| adb.exe (adbutils内置) | ✅ `C:\Python312\Lib\site-packages\adbutils\binaries\adb.exe` |
| ADB Server (5037) | ✅ 运行中 |
| Android USB 设备 | ❌ 未连接 |
| Android 无线设备 | ❌ 未连接 |

## 新模块功能清单 (14个函数)

| 函数 | 说明 |
|------|------|
| `devices()` | 列出已连接设备 |
| `ui()` | UI dump + 解析 (u2优先, adb回退) |
| `dump_ui()` | 仅dump UI XML |
| `tap(x, y)` | 点击坐标 |
| `swipe(x1,y1,x2,y2)` | 滑动 |
| `input_text(text)` | 输入文本 |
| `keyevent(code)` | 发送按键 |
| `screenshot(path)` | 截图 |
| `start_app(pkg)` | 启动应用 |
| `stop_app(pkg)` | 停止应用 |
| `current_app()` | 当前前台应用 |
| `connect_wireless(ip)` | 无线ADB连接 |
| `disconnect_wireless(ip)` | 无线ADB断开 |

## 与原 adb_ui.py 对比
- ✅ 去除了所有 subprocess 调用
- ✅ adbutils 自带 adb.exe，无需系统安装
- ✅ 新增: input_text, keyevent, screenshot, start/stop_app, wireless ADB
- ✅ 新增: CLI 命令行入口 (`python adb_ui_v2.py devices/ui/tap/swipe/...`)
- ✅ API 兼容: ui(), tap() 函数签名不变

## 阻塞项
- 无 Android 设备可测试端到端功能
- 代码逻辑已验证可导入，实际设备操作需用户在场时测试

## 记忆更新建议
- L3: adb_ui.py → adb_ui_v2.py (adbutils-based)
