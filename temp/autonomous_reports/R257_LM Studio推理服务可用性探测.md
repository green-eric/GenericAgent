# R261 LM Studio 推理服务可用性探测

## 结论
**❌ LM Studio 推理服务器当前不可用** — GUI 已启动但 API 服务未开启

## 探测过程

### 1. 安装状态
- 路径: `D:\Programs\LMS\LM Studio\`
- exe: `LM Studio.exe` ✅ 存在
- 版本: 目录结构完整（Electron 应用）

### 2. 进程状态
- 启动后产生 4 个子进程，总内存 ~700MB
- 最大进程 PID 16512 (350MB)

### 3. 端口探测
- Port 1234 (默认): ❌ closed
- Port 1235: ❌ closed
- 其他端口 (8080, 5000, 3000): ❌ closed

### 4. API 测试
- `GET /v1/models`: 连接被拒绝 (WinError 10061)

## 根因分析
LM Studio 是 **GUI-first** 应用：
- 启动 exe 只打开图形界面
- 推理服务器需要在 GUI 中手动点击 **"Start Server"** 按钮
- 无命令行参数可自动开启服务器模式

## 建议
1. **手动操作**: 打开 LM Studio → 点击 "Start Server" → 端口 1234 即开启
2. **自动化方案**: 考虑用 `pyautogui` 或 ADB 点击 GUI 按钮（需额外开发）
3. **替代方案**: 用 Ollama 替代 LM Studio，支持纯 CLI 启动服务

## 下一步
- 等用户手动开启服务器后，重新运行探测验证 API 连通性
- TODO 标记为部分完成（安装确认 ✅，服务可用性待验证）
